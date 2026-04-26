"""Result summarization for thesis experiment outputs."""

import statistics
from collections import defaultdict
from typing import Any

from .io import load_results
from .paths import RESULTS_FILE


def _count_statuses(experiments: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Count pass, fail, and error outcomes for a result slice."""
    passed = sum(
        1
        for experiment in experiments
        if experiment.get("validation") and experiment["validation"].get("overall_valid")
    )
    failed = sum(
        1
        for experiment in experiments
        if experiment.get("validation")
        and not experiment["validation"].get("overall_valid")
        and experiment["generation"]["success"]
    )
    errors = sum(1 for experiment in experiments if not experiment["generation"]["success"])
    return passed, failed, errors


def _group_results(
    results: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, list[dict[str, Any]]]]]:
    """Group experiment results by approach and tier."""
    by_approach: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_approach_tier: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for result in results:
        approach = result["approach"]
        tier = result.get("tier", "unknown")
        by_approach[approach].append(result)
        by_approach_tier[approach][tier].append(result)

    return by_approach, by_approach_tier


def _metric_means(experiments: list[dict[str, Any]]) -> dict[str, float]:
    """Compute mean values for the main experiment metrics."""
    return {
        "time": statistics.mean(experiment["generation"]["metrics"]["total_time"] for experiment in experiments),
        "llm_time": statistics.mean(
            experiment["generation"]["metrics"].get("llm_time", 0) for experiment in experiments
        ),
        "dsl_time": statistics.mean(
            experiment["generation"]["metrics"].get("dsl_time", 0) for experiment in experiments
        ),
        "input_tokens": statistics.mean(
            experiment["generation"]["metrics"]["input_tokens"] for experiment in experiments
        ),
        "output_tokens": statistics.mean(
            experiment["generation"]["metrics"]["output_tokens"] for experiment in experiments
        ),
        "total_tokens": statistics.mean(
            experiment["generation"]["metrics"]["total_tokens"] for experiment in experiments
        ),
    }


def _print_tier_breakdown(
    approach: str,
    by_approach_tier: dict[str, dict[str, list[dict[str, Any]]]],
) -> None:
    """Print per-tier success counts for one approach."""
    print("\nBreakdown by Tier:")
    for tier, tier_experiments in sorted(by_approach_tier[approach].items()):
        tier_passed, tier_failed, tier_errors = _count_statuses(tier_experiments)
        success_rate = (tier_passed / len(tier_experiments)) * 100 if tier_experiments else 0
        print(
            f"  - {tier.capitalize():<8}: {tier_passed}/{len(tier_experiments)} "
            f"({success_rate:.1f}%) [PASS: {tier_passed}, FAIL: {tier_failed}, ERR: {tier_errors}]"
        )


def _print_average_metrics(approach: str, experiments: list[dict[str, Any]]) -> None:
    """Print average timing and token metrics for one approach."""
    metrics = _metric_means(experiments)
    print("\nAverages:")
    print(f"  Time (Total):  {metrics['time']:.2f}s")
    print(f"    - LLM Gen:   {metrics['llm_time']:.2f}s")
    if approach == "dsl":
        print(f"    - DSL Exec:  {metrics['dsl_time']:.2f}s")

    print("  Tokens:")
    print(f"    - Input:     {metrics['input_tokens']:.1f}")
    print(f"    - Output:    {metrics['output_tokens']:.1f}")
    print(f"    - Total:     {metrics['total_tokens']:.1f}")


def _print_generation_errors(experiments: list[dict[str, Any]], errors: int) -> None:
    """Print generation errors for one approach if any exist."""
    if errors <= 0:
        return

    print("\nErrors encountered:")
    for experiment in experiments:
        if not experiment["generation"]["success"]:
            error_message = experiment["generation"].get("error", "Unknown error")
            print(f"  - {experiment['test_case']}: {error_message}")


def _print_approach_summary(
    approach: str,
    experiments: list[dict[str, Any]],
    by_approach_tier: dict[str, dict[str, list[dict[str, Any]]]],
) -> None:
    """Print the full summary for a single approach."""
    print(f"\n{approach.upper()} METHOD ({len(experiments)} runs)")
    print("-" * 40)

    passed, failed, errors = _count_statuses(experiments)
    print(
        f"Overall Success Rate: {passed}/{len(experiments)} "
        f"({(passed / len(experiments)) * 100:.1f}%)"
    )
    print(f"Overall Status: {passed} PASS, {failed} FAIL, {errors} ERR")
    _print_tier_breakdown(approach, by_approach_tier)
    _print_average_metrics(approach, experiments)
    _print_generation_errors(experiments, errors)


def analyze() -> None:
    """Print aggregate metrics from the saved experiment results."""
    results = load_results()
    if not results:
        print(f"No results found at {RESULTS_FILE}")
        return

    by_approach, by_approach_tier = _group_results(results)

    print(f"\nAnalysis of {len(results)} experiments")
    print("=" * 60)

    for approach, experiments in by_approach.items():
        _print_approach_summary(approach, experiments, by_approach_tier)


if __name__ == "__main__":
    analyze()
