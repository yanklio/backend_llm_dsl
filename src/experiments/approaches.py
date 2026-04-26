"""Generation approach implementations for thesis experiments."""

import time
from pathlib import Path
from typing import Any, Callable

from src.dsl.generate import main as dsl_generate
from src.llm import GenerationResult
from src.llm.dsl_generate import natural_language_to_yaml
from src.llm.mixed_generate import mixed_generate, save_mixed_files
from src.llm.raw_generate import generate_code_files, save_files

from .io import SuppressOutput
from .paths import blueprint_path_for


def _base_metrics(provider: str) -> dict[str, Any]:
    """Create the baseline metrics payload used by all approaches."""
    return {
        "llm_time": 0.0,
        "dsl_time": 0.0,
        "total_time": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "provider": provider,
    }


def _finish_metrics(metrics: dict[str, Any], start_time: float) -> dict[str, Any]:
    """Set total runtime before returning metrics."""
    metrics["total_time"] = time.time() - start_time
    return metrics


def _apply_generation_metrics(metrics: dict[str, Any], result: GenerationResult) -> None:
    """Copy standard generation stats into the shared metrics payload."""
    metrics["llm_time"] = result.duration_seconds
    metrics["input_tokens"] = result.input_tokens
    metrics["output_tokens"] = result.output_tokens
    metrics["total_tokens"] = result.total_tokens
    metrics["provider"] = result.provider


def _apply_mixed_metrics(metrics: dict[str, Any], stats: dict[str, Any]) -> None:
    """Copy normalized mixed-phase stats into the shared metrics payload."""
    metrics["llm_time"] = stats["total_duration_seconds"]
    metrics["input_tokens"] = stats.get("input_tokens", 0)
    metrics["output_tokens"] = stats.get("output_tokens", 0)
    metrics["total_tokens"] = stats.get("total_tokens", 0)
    metrics["provider"] = stats.get("provider")


def _run_with_timing(
    provider: str,
    operation: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    """Run one approach operation with shared timing and error handling."""
    start_time = time.time()
    metrics = _base_metrics(provider)

    try:
        operation(metrics)
        return {"success": True, "metrics": _finish_metrics(metrics, start_time)}
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "metrics": _finish_metrics(metrics, start_time),
        }


def run_dsl_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run the DSL experiment pipeline for one test case."""
    blueprint_path = blueprint_path_for(test_case_name, "_blueprint")
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)

    def operation(metrics: dict[str, Any]) -> None:
        with SuppressOutput():
            result: GenerationResult = natural_language_to_yaml(
                test_case_data["requirement"], provider=provider
            )

        _apply_generation_metrics(metrics, result)

        with open(blueprint_path, "w") as file_handle:
            file_handle.write(result.content)

        dsl_start = time.time()
        with SuppressOutput():
            dsl_generate(str(blueprint_path), str(project_path))
        metrics["dsl_time"] = time.time() - dsl_start

    return _run_with_timing(provider, operation)


def run_raw_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run the raw-code experiment pipeline for one test case."""
    del test_case_name

    def operation(metrics: dict[str, Any]) -> None:
        with SuppressOutput():
            result, files = generate_code_files(
                test_case_data["requirement"], str(project_path), provider=provider
            )
            save_files(files, str(project_path))

        _apply_generation_metrics(metrics, result)

    return _run_with_timing(provider, operation)


def run_mixed_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run the mixed blueprint-plus-code experiment pipeline for one test case."""
    blueprint_path = blueprint_path_for(test_case_name, "_mixed_blueprint")
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)

    def operation(metrics: dict[str, Any]) -> None:
        with SuppressOutput():
            result = mixed_generate(
                description=test_case_data["requirement"],
                output_dir=str(project_path),
                blueprint_path=str(blueprint_path),
                primary_model=provider,
            )

            if result["success"]:
                save_mixed_files(result["files"], str(project_path))
            else:
                raise Exception(result.get("error", "Unknown mixed generation error"))

        _apply_mixed_metrics(metrics, result["statistics"])

    return _run_with_timing(provider, operation)


APPROACH_RUNNERS = {
    "dsl": run_dsl_approach,
    "raw": run_raw_approach,
    "mixed": run_mixed_approach,
}
