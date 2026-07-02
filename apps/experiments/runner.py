"""CLI and orchestration for benchmark experiment runs."""

import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from packages.llm_providers.evaluation.prompt_alignment import (
    DEFAULT_ALIGNMENT_MODEL,
    DEFAULT_ALIGNMENT_PROVIDER,
    PROMPT_ALIGNMENT_VERSION,
    evaluate_prompt_alignment,
    prompt_alignment_prompt_hash,
)

from .approaches import APPROACH_RUNNERS
from .io import SuppressOutput, load_results, load_test_cases, save_json, save_results
from .metadata import build_run_metadata, record_identity, resume_key
from .paths import NEST_PROJECT_DIR, RUNS_DIR
from .project import clean_project, ensure_base_project, validate_project


def _selected_approaches(approach: str) -> list[str]:
    """Normalize CLI approach selection into a concrete list."""
    return (
        ["dsl", "raw", "mixed", "textual-gen-baseline", "textual-gen-spec", "textual-gen-fewshot"]
        if approach == "all"
        else [approach]
    )


def _print_run_header(test_cases_count: int) -> None:
    """Print the standard experiment table header."""
    print(f"Starting experiments for {test_cases_count} test cases...")
    print(f"{'Test Case':<15} {'Tier':<8} {'Approach':<10} {'Status':<10} {'Time':<8} {'Tokens':<8}")
    print("-" * 70)


def _completed_run_keys(results: list[dict[str, Any]]) -> set[tuple[str, ...]]:
    """Build the resume keys for completed experiment runs."""
    return {resume_key(result) for result in results}


def _build_result_record(
    case_name: str,
    tier: str,
    approach: str,
    provider: str,
    generation: dict[str, Any],
    validation: dict[str, Any],
    run_id: str,
    repetition: int | dict[str, Any] = 1,
    prompt_alignment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the persisted result payload for one run."""
    if isinstance(repetition, dict) and prompt_alignment is None:
        prompt_alignment = repetition
        repetition = 1
    identity = record_identity(
        provider=provider,
        approach=approach,
        test_case=case_name,
        tier=tier,
        repetition=int(repetition),
    )
    record = {
        **identity,
        "run_id": run_id,
        "generation": generation,
        "validation": validation,
        "timestamp": datetime.now().isoformat(),
    }
    if prompt_alignment is not None:
        record["prompt_alignment"] = prompt_alignment
    return record


def _validate_generation(generation: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Run project validation if generation succeeded and return status."""
    if not generation["success"]:
        return {}, "ERR"

    validation = validate_project(NEST_PROJECT_DIR)
    status = "PASS" if validation["overall_valid"] else "FAIL"
    return validation, status


def _empty_prompt_alignment(
    *,
    provider: str,
    model_name: str,
    error: str,
) -> dict[str, Any]:
    """Create a recorded prompt-alignment payload when judging cannot run."""
    return {
        "provider": provider,
        "model_name": model_name,
        "prompt_version": PROMPT_ALIGNMENT_VERSION,
        "prompt_hash": prompt_alignment_prompt_hash(),
        "metrics": {
            "duration_seconds": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        },
        "source_files": {"count": 0, "total_characters": 0},
        "result": None,
        "error": error,
    }


def _run_prompt_alignment(
    *,
    case_data: dict[str, Any],
    generation: dict[str, Any],
    provider: str,
    model_name: str,
) -> dict[str, Any]:
    """Run prompt-alignment judging without changing validation status."""
    if not generation["success"]:
        return _empty_prompt_alignment(
            provider=provider,
            model_name=model_name,
            error="generation_failed",
        )

    try:
        with SuppressOutput():
            return evaluate_prompt_alignment(
                requirement=case_data["requirement"],
                endpoints=case_data.get("endpoints", []),
                project_dir=NEST_PROJECT_DIR,
                provider=provider,
                model_name=model_name,
            )
    except (RuntimeError, ValueError, OSError) as exc:
        return _empty_prompt_alignment(
            provider=provider,
            model_name=model_name,
            error=str(exc),
        )


def _print_run_result(
    case_name: str,
    tier: str,
    approach: str,
    status: str,
    generation: dict[str, Any],
) -> None:
    """Print one experiment result row."""
    metrics = generation["metrics"]
    print(
        f"{case_name:<15} {tier:<8} {approach:<10} {status:<10} "
        f"{metrics['total_time']:.2f}s   {str(metrics['total_tokens']):<8}"
    )
    if status == "ERR":
        print(f"  Error: {generation.get('error', 'Unknown')}")


def _prepare_project() -> None:
    """Reset and scaffold the generated Nest project directory."""
    clean_project(NEST_PROJECT_DIR)
    ensure_base_project(NEST_PROJECT_DIR)


def _run_results_file(run_dir: Path) -> Path:
    """Return the aggregate results path for one experiment invocation."""
    return run_dir / "results.json"


def _record_file(run_dir: Path, case_name: str, approach: str, repetition: int) -> Path:
    """Return the per-case result record path inside a run directory."""
    return run_dir / "records" / f"{case_name}_{approach}_rep-{repetition}.json"


def _artifact_dir(run_dir: Path, case_name: str, approach: str, repetition: int) -> Path:
    """Return the complete artifact directory for one record."""
    return run_dir / "cases" / case_name / approach / f"rep-{repetition}"


def _create_run_dir(run_metadata: dict[str, Any]) -> Path:
    """Create a timestamped run directory and write its metadata file."""
    run_dir = RUNS_DIR / run_metadata["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    save_json(run_dir / "metadata.json", run_metadata)
    save_json(_run_results_file(run_dir), [])
    return run_dir


def _save_record(
    record: dict[str, Any],
    *,
    run_dir: Path,
    run_results: list[dict[str, Any]],
) -> None:
    """Persist one record to the immutable run folder only."""
    run_results.append(record)
    save_json(_record_file(run_dir, record["test_case"], record["approach"], record["repetition"]), record)
    save_results(run_results, _run_results_file(run_dir))
    save_json(run_dir / "latest.json", {"results": str(_run_results_file(run_dir))})


def _copytree_ignore(_dir: str, names: list[str]) -> set[str]:
    return {name for name in names if name in {"node_modules", "dist", ".coverage"}}


def _write_if_present(path: Path, value: object | None) -> None:
    """Write an artifact file when a value is available."""
    if value is not None:
        path.write_text(str(value))


def _write_generation_artifacts(generation_dir: Path, generation: dict[str, Any]) -> None:
    """Write normalized generation artifacts captured by approach runners."""
    metrics = generation.get("metrics", {})
    _write_if_present(generation_dir / "raw-response.txt", metrics.get("raw_response"))
    _write_if_present(generation_dir / "cleaned-response.txt", metrics.get("cleaned_response"))
    _write_if_present(generation_dir / "textual.dsl", metrics.get("textual_dsl"))
    _write_if_present(generation_dir / "phase-1-raw-response.txt", metrics.get("phase1_raw_response"))
    _write_if_present(generation_dir / "phase-2-raw-response.txt", metrics.get("phase2_raw_response"))
    blueprint_path = metrics.get("artifact_blueprint_path")
    if blueprint_path and Path(str(blueprint_path)).exists():
        shutil.copyfile(str(blueprint_path), generation_dir / "blueprint.yaml")


def _save_artifacts(
    artifact_dir: Path,
    case_data: dict[str, Any],
    generation: dict[str, Any],
    validation: dict[str, Any],
    prompt_alignment: dict[str, Any] | None,
) -> None:
    """Persist best-effort artifacts for a case/approach/repetition."""
    generation_dir = artifact_dir / "generation"
    logs_dir = artifact_dir / "logs"
    generation_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "requirement.txt").write_text(case_data.get("requirement", ""))
    save_json(artifact_dir / "validation.json", validation)
    save_json(artifact_dir / "judge.json", prompt_alignment or {"enabled": False})
    save_json(artifact_dir / "record.json", generation)
    _write_generation_artifacts(generation_dir, generation)
    (logs_dir / "generation.log").write_text(generation.get("error", ""))
    (logs_dir / "validation.log").write_text(str(validation))
    if NEST_PROJECT_DIR.exists():
        shutil.copytree(
            NEST_PROJECT_DIR,
            artifact_dir / "generated-project",
            dirs_exist_ok=True,
            ignore=_copytree_ignore,
        )


def _selected_test_cases(
    test_cases: dict[str, Any],
    case_id: str | None,
    limit: int | None,
) -> dict[str, Any]:
    """Select a subset of test cases for smoke or partial runs."""
    if case_id:
        if case_id not in test_cases:
            raise ValueError(f"Unknown test case: {case_id}")
        return {case_id: test_cases[case_id]}

    if limit is None:
        return test_cases

    return dict(list(test_cases.items())[:limit])


def _run_case(
    case_name: str,
    case_data: dict[str, Any],
    tier: str,
    current_approach: str,
    provider: str,
    run_metadata: dict[str, Any],
    run_dir: Path,
    run_results: list[dict[str, Any]],
    judge_enabled: bool,
    judge_provider: str,
    judge_model: str,
    repetition: int,
) -> None:
    """Run, validate, print, and persist one experiment case."""
    _prepare_project()
    generation = APPROACH_RUNNERS[current_approach](
        case_name,
        case_data,
        NEST_PROJECT_DIR,
        provider=provider,
    )

    validation, status = _validate_generation(generation)
    _print_run_result(case_name, tier, current_approach, status, generation)
    prompt_alignment = None
    if judge_enabled:
        prompt_alignment = _run_prompt_alignment(
            case_data=case_data,
            generation=generation,
            provider=judge_provider,
            model_name=judge_model,
        )

    record = _build_result_record(
        case_name,
        tier,
        current_approach,
        provider,
        generation,
        validation,
        run_metadata["run_id"],
        repetition,
        prompt_alignment,
    )
    artifact_dir = _artifact_dir(run_dir, case_name, current_approach, repetition)
    _save_artifacts(artifact_dir, case_data, generation, validation, prompt_alignment)
    _save_record(
        record,
        run_dir=run_dir,
        run_results=run_results,
    )


def run_experiments(
    approach: str = "all",
    provider: str = "openrouter",
    case_id: str | None = None,
    limit: int | None = None,
    judge_enabled: bool = False,
    judge_provider: str = DEFAULT_ALIGNMENT_PROVIDER,
    judge_model: str = DEFAULT_ALIGNMENT_MODEL,
    repetitions: int = 1,
) -> None:
    """Execute generation experiments across the configured test cases."""
    approaches_to_run = _selected_approaches(approach)
    print(f"Using provider: {provider}")
    run_metadata = build_run_metadata(provider, approaches_to_run, repetitions)
    run_metadata["prompt_alignment"] = {
        "enabled": judge_enabled,
        "provider": judge_provider if judge_enabled else None,
        "model_name": judge_model if judge_enabled else None,
        "prompt_version": PROMPT_ALIGNMENT_VERSION if judge_enabled else None,
        "prompt_hash": prompt_alignment_prompt_hash() if judge_enabled else None,
    }
    run_dir = _create_run_dir(run_metadata)
    print(f"Run ID: {run_metadata['run_id']}")
    print(f"Run directory: {run_dir}")

    test_cases = _selected_test_cases(load_test_cases(), case_id, limit)
    NEST_PROJECT_DIR.mkdir(exist_ok=True)

    run_results = load_results(_run_results_file(run_dir))
    completed_runs = _completed_run_keys(run_results)

    _print_run_header(len(test_cases))

    for repetition in range(1, repetitions + 1):
        for case_name, case_data in test_cases.items():
            tier = case_data.get("tier", "unknown")
            for current_approach in approaches_to_run:
                current_identity = record_identity(
                    provider=provider,
                    approach=current_approach,
                    test_case=case_name,
                    tier=tier,
                    repetition=repetition,
                )
                if resume_key(current_identity) in completed_runs:
                    print(f"Skipping {case_name} ({current_approach}) rep-{repetition} - already completed")
                    continue

                _run_case(
                    case_name,
                    case_data,
                    tier,
                    current_approach,
                    provider,
                    run_metadata,
                    run_dir,
                    run_results,
                    judge_enabled,
                    judge_provider,
                    judge_model,
                    repetition,
                )

    print("-" * 70)
    print(f"Run results saved to {_run_results_file(run_dir)}")
    print("Timestamped run directory is authoritative; legacy aggregate was not updated.")


def main() -> None:
    """Parse CLI arguments and execute experiments."""
    parser = argparse.ArgumentParser(description="Run generation experiments.")
    parser.add_argument(
        "--approach",
        choices=["dsl", "raw", "mixed", "textual-gen-baseline", "textual-gen-spec", "textual-gen-fewshot", "all"],
        default="all",
        help="Which approach to run",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "gemini", "openrouter", "ollama"],
        default="openrouter",
        help="LLM provider to use (default: openrouter)",
    )
    parser.add_argument(
        "--case",
        dest="case_id",
        default=None,
        help="Run one specific test case ID, e.g. TEST_CASE_12",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N test cases for smoke testing",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Record LLM prompt-alignment scores after generation and validation",
    )
    parser.add_argument(
        "--judge-provider",
        choices=["groq", "gemini", "openrouter", "ollama"],
        default=DEFAULT_ALIGNMENT_PROVIDER,
        help="LLM provider for prompt-alignment judging",
    )
    parser.add_argument(
        "--judge-model",
        default=DEFAULT_ALIGNMENT_MODEL,
        help="Exact model for prompt-alignment judging",
    )
    parser.add_argument("--repetitions", type=int, default=1)
    args = parser.parse_args()
    run_experiments(
        approach=args.approach,
        provider=args.provider,
        case_id=args.case_id,
        limit=args.limit,
        judge_enabled=args.judge,
        judge_provider=args.judge_provider,
        judge_model=args.judge_model,
        repetitions=args.repetitions,
    )


if __name__ == "__main__":
    main()
