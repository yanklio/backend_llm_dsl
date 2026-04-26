"""CLI and orchestration for benchmark experiment runs."""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from .approaches import APPROACH_RUNNERS
from .io import load_results, load_test_cases, save_json, save_results
from .metadata import build_run_metadata, record_identity, resume_key
from .paths import NEST_PROJECT_DIR, RESULTS_FILE, RUNS_DIR
from .project import clean_project, ensure_base_project, validate_project


def _selected_approaches(approach: str) -> list[str]:
    """Normalize CLI approach selection into a concrete list."""
    return ["dsl", "raw", "mixed"] if approach == "all" else [approach]


def _print_run_header(test_cases_count: int) -> None:
    """Print the standard experiment table header."""
    print(f"Starting experiments for {test_cases_count} test cases...")
    print(
        f"{'Test Case':<15} {'Tier':<8} {'Approach':<10} {'Status':<10} {'Time':<8} {'Tokens':<8}"
    )
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
) -> dict[str, Any]:
    """Create the persisted result payload for one run."""
    identity = record_identity(
        provider=provider,
        approach=approach,
        test_case=case_name,
        tier=tier,
    )
    return {
        **identity,
        "run_id": run_id,
        "generation": generation,
        "validation": validation,
        "timestamp": datetime.now().isoformat(),
    }


def _validate_generation(generation: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Run project validation if generation succeeded and return status."""
    if not generation["success"]:
        return {}, "ERR"

    validation = validate_project(NEST_PROJECT_DIR)
    status = "PASS" if validation["overall_valid"] else "FAIL"
    return validation, status


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


def _record_file(run_dir: Path, case_name: str, approach: str) -> Path:
    """Return the per-case result record path inside a run directory."""
    return run_dir / "records" / f"{case_name}_{approach}.json"


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
    legacy_results: list[dict[str, Any]],
) -> None:
    """Persist one record to both the immutable run folder and legacy aggregate file."""
    run_results.append(record)
    legacy_results.append(record)
    save_json(_record_file(run_dir, record["test_case"], record["approach"]), record)
    save_results(run_results, _run_results_file(run_dir))
    save_results(legacy_results, RESULTS_FILE)


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
    legacy_results: list[dict[str, Any]],
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

    record = _build_result_record(
        case_name,
        tier,
        current_approach,
        provider,
        generation,
        validation,
        run_metadata["run_id"],
    )
    _save_record(
        record,
        run_dir=run_dir,
        run_results=run_results,
        legacy_results=legacy_results,
    )


def run_experiments(
    approach: str = "all",
    provider: str = "openrouter",
    case_id: str | None = None,
    limit: int | None = None,
) -> None:
    """Execute generation experiments across the configured test cases."""
    approaches_to_run = _selected_approaches(approach)
    print(f"Using provider: {provider}")
    run_metadata = build_run_metadata(provider, approaches_to_run)
    run_dir = _create_run_dir(run_metadata)
    print(f"Run ID: {run_metadata['run_id']}")
    print(f"Run directory: {run_dir}")

    test_cases = _selected_test_cases(load_test_cases(), case_id, limit)
    NEST_PROJECT_DIR.mkdir(exist_ok=True)

    run_results = load_results(_run_results_file(run_dir))
    legacy_results = load_results(RESULTS_FILE)
    completed_runs = _completed_run_keys(run_results)

    _print_run_header(len(test_cases))

    for case_name, case_data in test_cases.items():
        tier = case_data.get("tier", "unknown")
        for current_approach in approaches_to_run:
            current_identity = record_identity(
                provider=provider,
                approach=current_approach,
                test_case=case_name,
                tier=tier,
            )
            if resume_key(current_identity) in completed_runs:
                print(f"Skipping {case_name} ({current_approach}) - already completed")
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
                legacy_results,
            )

    print("-" * 70)
    print(f"Run results saved to {_run_results_file(run_dir)}")
    print(f"Legacy aggregate results updated at {RESULTS_FILE}")


def main() -> None:
    """Parse CLI arguments and execute experiments."""
    parser = argparse.ArgumentParser(description="Run generation experiments.")
    parser.add_argument(
        "--approach",
        choices=["dsl", "raw", "mixed", "all"],
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
    args = parser.parse_args()
    run_experiments(
        approach=args.approach,
        provider=args.provider,
        case_id=args.case_id,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
