import json
import statistics
from collections import defaultdict
from pathlib import Path


def analyze():
    results_path = Path(__file__).parent / "test_results.json"
    if not results_path.exists():
        print(f"No results found at {results_path}")
        return

    with open(results_path) as f:
        results = json.load(f)

    # Group by approach and tier
    by_approach = defaultdict(list)
    by_approach_tier = defaultdict(lambda: defaultdict(list))

    for r in results:
        by_approach[r["approach"]].append(r)
        tier = r.get("tier", "unknown")
        by_approach_tier[r["approach"]][tier].append(r)

    print(f"\nAnalysis of {len(results)} experiments")
    print("=" * 60)

    for approach, experiments in by_approach.items():
        print(f"\n{approach.upper()} METHOD ({len(experiments)} runs)")
        print("-" * 40)

        # Validation stats
        passed = sum(1 for e in experiments if e.get("validation") and e["validation"].get("overall_valid"))
        failed = sum(1 for e in experiments if e.get("validation") and not e["validation"].get("overall_valid") and e["generation"]["success"])
        errors = sum(1 for e in experiments if not e["generation"]["success"])

        print(f"Overall Success Rate: {passed}/{len(experiments)} ({(passed/len(experiments))*100:.1f}%)")
        print(f"Overall Status: {passed} PASS, {failed} FAIL, {errors} ERR")
        
        # Breakdown by tier
        print("\nBreakdown by Tier:")
        for tier, tier_exps in sorted(by_approach_tier[approach].items()):
            tier_passed = sum(1 for e in tier_exps if e.get("validation") and e["validation"].get("overall_valid"))
            tier_failed = sum(1 for e in tier_exps if e.get("validation") and not e["validation"].get("overall_valid") and e["generation"]["success"])
            tier_errors = sum(1 for e in tier_exps if not e["generation"]["success"])
            success_rate = (tier_passed / len(tier_exps)) * 100 if tier_exps else 0
            print(f"  - {tier.capitalize():<8}: {tier_passed}/{len(tier_exps)} ({success_rate:.1f}%) [PASS: {tier_passed}, FAIL: {tier_failed}, ERR: {tier_errors}]")

        # Time Metrics
        times = [e["generation"]["metrics"]["total_time"] for e in experiments]
        llm_times = [e["generation"]["metrics"].get("llm_time", 0) for e in experiments]
        dsl_times = [e["generation"]["metrics"].get("dsl_time", 0) for e in experiments]

        # Token Metrics
        in_tokens = [e["generation"]["metrics"]["input_tokens"] for e in experiments]
        out_tokens = [e["generation"]["metrics"]["output_tokens"] for e in experiments]
        total_tokens = [e["generation"]["metrics"]["total_tokens"] for e in experiments]

        print("\nAverages:")
        print(f"  Time (Total):  {statistics.mean(times):.2f}s")
        print(f"    - LLM Gen:   {statistics.mean(llm_times):.2f}s")
        if approach == "dsl":
            print(f"    - DSL Exec:  {statistics.mean(dsl_times):.2f}s")
            
        print("  Tokens:")
        print(f"    - Input:     {statistics.mean(in_tokens):.1f}")
        print(f"    - Output:    {statistics.mean(out_tokens):.1f}")
        print(f"    - Total:     {statistics.mean(total_tokens):.1f}")

        if errors > 0:
            print("\nErrors encountered:")
            for e in experiments:
                if not e["generation"]["success"]:
                    error_msg = e["generation"].get("error", "Unknown error")
                    print(f"  - {e['test_case']}: {error_msg}")

if __name__ == "__main__":
    analyze()
