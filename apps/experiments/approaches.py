"""Generation approach implementations for thesis experiments."""

import time
from pathlib import Path
from typing import Any, Callable

import yaml

from packages.dsl_core.compiler import compile_textual_dsl
from packages.generator_nestjs.generate import generate_from_file
from packages.llm_providers import GenerationResult, LLMClient
from packages.llm_providers.core.prompts import TextualPromptVariant, build_textual_generation_messages
from packages.llm_providers.core.response_parser import clean_llm_response
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


class GenerationPipelineError(RuntimeError):
    """Raised when an experiment generation pipeline returns a failure result."""


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
    except (ValueError, RuntimeError, OSError) as exc:
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
            result: GenerationResult = natural_language_to_yaml(test_case_data["requirement"], provider=provider)

        _apply_generation_metrics(metrics, result)

        with open(blueprint_path, "w") as file_handle:
            file_handle.write(result.content)
        metrics["artifact_blueprint_path"] = str(blueprint_path)
        metrics["raw_response"] = result.raw_content or result.content
        metrics["cleaned_response"] = result.content

        dsl_start = time.perf_counter()
        with SuppressOutput():
            generate_from_file(str(blueprint_path), str(project_path))
        metrics["dsl_time"] = time.perf_counter() - dsl_start

    return _run_with_timing(provider, operation)


def run_raw_approach(
    _test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run the raw-code experiment pipeline for one test case."""

    def operation(metrics: dict[str, Any]) -> None:
        with SuppressOutput():
            result, files = generate_code_files(test_case_data["requirement"], str(project_path), provider=provider)
            save_files(files, str(project_path))

        _apply_generation_metrics(metrics, result)
        metrics["raw_response"] = result.raw_content or result.content
        metrics["cleaned_response"] = result.content

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
                raise GenerationPipelineError(result.get("error", "Unknown mixed generation error"))

        _apply_mixed_metrics(metrics, result["statistics"])
        metrics["artifact_blueprint_path"] = str(blueprint_path)
        metrics["phase1_raw_response"] = result.get("phase1_raw_response", result.get("blueprint", ""))
        metrics["phase2_raw_response"] = result.get("code_response", "")

    return _run_with_timing(provider, operation)


def run_textual_gen_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
    variant: str = "spec",
) -> dict[str, Any]:
    """Run the LLM-generates-textual-DSL approach.

    LLM generates textual DSL source code from natural language.
    Deterministic compiler converts DSL -> YAML blueprint.
    Jinja2 generator converts blueprint -> NestJS code.
    """
    blueprint_path = blueprint_path_for(test_case_name, "_textual_gen_blueprint")
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)

    def operation(metrics: dict[str, Any]) -> None:
        client = LLMClient(provider_id=provider, temperature=0.1)
        messages = build_textual_generation_messages(test_case_data["requirement"], TextualPromptVariant(variant))

        with SuppressOutput():
            result = client.generate(messages)
        result.raw_content = result.content
        result.content = clean_llm_response(result.content)

        _apply_generation_metrics(metrics, result)

        with SuppressOutput():
            blueprint = compile_textual_dsl(result.content)

        with open(blueprint_path, "w") as f:
            yaml.safe_dump(blueprint, f, sort_keys=False)
        metrics["artifact_blueprint_path"] = str(blueprint_path)
        metrics["raw_response"] = result.raw_content or result.content
        metrics["cleaned_response"] = result.content
        metrics["textual_dsl"] = result.content

        dsl_start = time.perf_counter()
        with SuppressOutput():
            generate_from_file(str(blueprint_path), str(project_path))
        metrics["dsl_time"] = time.perf_counter() - dsl_start

    return _run_with_timing(provider, operation)


def run_textual_gen_baseline_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run baseline textual generation."""
    return run_textual_gen_approach(test_case_name, test_case_data, project_path, provider=provider, variant="baseline")


def run_textual_gen_spec_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run specification textual generation."""
    return run_textual_gen_approach(test_case_name, test_case_data, project_path, provider=provider, variant="spec")


def run_textual_gen_fewshot_approach(
    test_case_name: str,
    test_case_data: dict[str, Any],
    project_path: Path,
    provider: str = "openrouter",
) -> dict[str, Any]:
    """Run few-shot textual generation."""
    return run_textual_gen_approach(test_case_name, test_case_data, project_path, provider=provider, variant="fewshot")


APPROACH_RUNNERS = {
    "dsl": run_dsl_approach,
    "raw": run_raw_approach,
    "textual-gen-baseline": run_textual_gen_baseline_approach,
    "textual-gen-spec": run_textual_gen_spec_approach,
    "textual-gen-fewshot": run_textual_gen_fewshot_approach,
    "mixed": run_mixed_approach,
}
