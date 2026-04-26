"""CLI and orchestration for benchmark experiment runs."""

import argparse
from datetime import datetime
from typing import Any

from .approaches import APPROACH_RUNNERS
from .io import load_results, load_test_cases, save_results
from .paths import NEST_PROJECT_DIR, RESULTS_FILE
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


def _build_result_record(
    case_name: str,
    tier: str,
    approach: str,
    generation: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    """Create the persisted result payload for one run."""
    return {
        "test_case": case_name,
        "tier": tier,
        "approach": approach,
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


def run_experiments(approach: str = "all", provider: str = "openrouter") -> None:
    """Execute generation experiments across the configured test cases."""
    approaches_to_run = _selected_approaches(approach)
    print(f"Using provider: {provider}")

    test_cases = load_test_cases()
    NEST_PROJECT_DIR.mkdir(exist_ok=True)

    results = load_results()
    completed_runs = {(result["test_case"], result["approach"]) for result in results}

    _print_run_header(len(test_cases))

    for case_name, case_data in test_cases.items():
        tier = case_data.get("tier", "unknown")
        for current_approach in approaches_to_run:
            if (case_name, current_approach) in completed_runs:
                print(f"Skipping {case_name} ({current_approach}) - already completed")
                continue

            clean_project(NEST_PROJECT_DIR)
            ensure_base_project(NEST_PROJECT_DIR)
            generation = APPROACH_RUNNERS[current_approach](
                case_name,
                case_data,
                NEST_PROJECT_DIR,
                provider=provider,
            )

            validation, status = _validate_generation(generation)
            _print_run_result(case_name, tier, current_approach, status, generation)

            results.append(
                _build_result_record(
                    case_name,
                    tier,
                    current_approach,
                    generation,
                    validation,
                )
            )
            save_results(results)

    print("-" * 70)
    print(f"Results saved to {RESULTS_FILE}")


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
    args = parser.parse_args()
    run_experiments(approach=args.approach, provider=args.provider)


if __name__ == "__main__":
    main()
