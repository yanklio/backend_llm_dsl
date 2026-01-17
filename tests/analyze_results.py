
import json
from pathlib import Path
from collections import defaultdict
import statistics

def analyze():
    results_path = Path(__file__).parent / "test_results.json"
    if not results_path.exists():
        print(f"No results found at {results_path}")
        return

    with open(results_path, "r") as f:
        results = json.load(f)

    # Group by approach
    by_approach = defaultdict(list)
    for r in results:
        by_approach[r["approach"]].append(r)

    print(f"\nAnalysis of {len(results)} experiments")
    print("=" * 60)

    for approach, experiments in by_approach.items():
        print(f"\n{approach.upper()} METHOD ({len(experiments)} runs)")
        print("-" * 40)

        # Metrics
        times = [e["generation"]["metrics"]["total_time"] for e in experiments]
        llm_times = [e["generation"]["metrics"].get("llm_time", 0) for e in experiments]
        dsl_times = [e["generation"]["metrics"].get("dsl_time", 0) for e in experiments]
        
        in_tokens = [e["generation"]["metrics"]["input_tokens"] for e in experiments]
        out_tokens = [e["generation"]["metrics"]["output_tokens"] for e in experiments]
        total_tokens = [e["generation"]["metrics"]["total_tokens"] for e in experiments]

        # Validation
        passed = sum(1 for e in experiments if e["validation"].get("overall_valid"))
        failed = sum(1 for e in experiments if not e["validation"].get("overall_valid") and e["generation"]["success"])
        errors = sum(1 for e in experiments if not e["generation"]["success"])

        print(f"Success Rate: {passed}/{len(experiments)} ({(passed/len(experiments))*100:.1f}%)")
        print(f"Status: {passed} PASS, {failed} FAIL, {errors} ERR")
        print(f"\nAverages:")
        print(f"  Time (Total):  {statistics.mean(times):.2f}s")
        print(f"    - LLM Gen:   {statistics.mean(llm_times):.2f}s")
        if approach == "dsl":
            print(f"    - DSL Exec:  {statistics.mean(dsl_times):.2f}s")
            
        print(f"  Tokens:")
        print(f"    - Input:     {statistics.mean(in_tokens):.1f}")
        print(f"    - Output:    {statistics.mean(out_tokens):.1f}")
        print(f"    - Total:     {statistics.mean(total_tokens):.1f}")

        if errors > 0:
            print(f"\nErrors encountered:")
            for e in experiments:
                if not e["generation"]["success"]:
                    print(f"  - {e['test_case']}: {e['generation'].get('error', 'Unknown')}")

if __name__ == "__main__":
    analyze()
