"""Generation approach implementations for thesis experiments."""

import time
from pathlib import Path
from typing import Any, Callable

from packages.generator_nestjs.generate import main as dsl_generate
from packages.llm_providers import GenerationResult
from packages.llm_providers.generators.dsl_generate import natural_language_to_yaml
from packages.llm_providers.generators.mixed_generate import mixed_generate, save_mixed_files
from packages.llm_providers.generators.raw_generate import generate_code_files, save_files

from .io import SuppressOutput
from .metadata import model_name_for_provider
from .paths import blueprint_path_for

MIXED_PHASE_METRIC_FIELDS = (
    "phase1_input_tokens",
    "phase1_output_tokens",
    "phase1_total_tokens",
    "phase2_input_tokens",
    "phase2_output_tokens",
    "phase2_total_tokens",
)


def _base_metrics(provider: str) -> dict[str, Any]:
    """Create the baseline metrics payload used by all approaches."""
    return {
        "llm_time": 0.0,
        "dsl_time": 0.0,
        "total_time": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "provider_id": provider,
        "provider": provider,
        "model_name": model_name_for_provider(provider),
    }


def _finish_metrics(metrics: dict[str, Any], start_time: float) -> dict[str, Any]:
    """Set total runtime before returning metrics."""
    metrics["total_time"] = time.perf_counter() - start_time
    return metrics


def _apply_generation_metrics(metrics: dict[str, Any], result: GenerationResult) -> None:
    """Copy standard generation stats into the shared metrics payload."""
    metrics["llm_time"] = result.duration_seconds
    metrics["input_tokens"] = result.input_tokens
    metrics["output_tokens"] = result.output_tokens
    metrics["total_tokens"] = result.total_tokens
    metrics["provider"] = result.provider
    metrics["model_name"] = result.model_name


def _apply_mixed_metrics(metrics: dict[str, Any], stats: dict[str, Any]) -> None:
    """Copy normalized mixed-phase stats into the shared metrics payload."""
    metrics["llm_time"] = stats["total_duration_seconds"]
    metrics["input_tokens"] = stats.get("input_tokens", 0)
    metrics["output_tokens"] = stats.get("output_tokens", 0)
    metrics["total_tokens"] = stats.get("total_tokens", 0)
    metrics["provider"] = stats.get("provider")
    metrics["model_name"] = stats.get("model_name")
    for field_name in MIXED_PHASE_METRIC_FIELDS:
        metrics[field_name] = stats.get(field_name, 0)


def _run_with_timing(
    provider: str,
    operation: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    """Run one approach operation with shared timing and error handling."""
    start_time = time.perf_counter()
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

        dsl_start = time.perf_counter()
        with SuppressOutput():
            dsl_generate(str(blueprint_path), str(project_path))
        metrics["dsl_time"] = time.perf_counter() - dsl_start

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


def run_textual_gen_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run the LLM-generates-textual-DSL approach.

    LLM generates textual DSL source code from natural language.
    Deterministic compiler converts DSL -> YAML blueprint.
    Jinja2 generator converts blueprint -> NestJS code.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from packages.dsl_core.compiler import compile_textual_dsl
    from packages.llm_providers import LLMClient
    from packages.llm_providers.core.prompts import TEXTUAL_GEN_SYSTEM_PROMPT
    from packages.llm_providers.core.response_parser import clean_llm_response

    blueprint_path = blueprint_path_for(test_case_name, "_textual_gen_blueprint")
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)

    def operation(metrics: dict[str, Any]) -> None:
        client = LLMClient(provider_id=provider, temperature=0.1)
        messages = [
            SystemMessage(content=TEXTUAL_GEN_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Generate textual DSL source code for this NestJS application:\n\n"
                    f"{test_case_data['requirement']}"
                )
            ),
        ]

        with SuppressOutput():
            result = client.generate(messages)
        result.content = clean_llm_response(result.content)

        _apply_generation_metrics(metrics, result)

        with SuppressOutput():
            blueprint = compile_textual_dsl(result.content)

        with open(blueprint_path, "w") as f:
            import yaml

            yaml.safe_dump(blueprint, f, sort_keys=False)

        dsl_start = time.perf_counter()
        with SuppressOutput():
            dsl_generate(str(blueprint_path), str(project_path))
        metrics["dsl_time"] = time.perf_counter() - dsl_start

    return _run_with_timing(provider, operation)


APPROACH_RUNNERS = {
    "dsl": run_dsl_approach,
    "raw": run_raw_approach,
    "textual-gen": run_textual_gen_approach,
    "mixed": run_mixed_approach,
}
