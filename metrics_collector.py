#!/usr/bin/env python3
"""
Metrics Collector for DSL-based Code Generation
Measures consistency, quality, and performance improvements
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Any

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from llm.yaml_generator_multi import natural_language_to_yaml

load_dotenv()


class MetricsCollector:
    """Collects metrics on code generation consistency and quality"""

    def __init__(self, output_dir: str = "./metrics_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "consistency_tests": [],
            "performance_tests": [],
            "quality_metrics": [],
        }

    def measure_consistency(
        self, description: str, num_runs: int = 5
    ) -> Dict[str, Any]:
        """
        Run the same description multiple times and measure consistency
        """
        print(f"\n📊 Measuring consistency for: '{description}'")
        print(f"   Running {num_runs} iterations...")

        blueprints = []
        generation_times = []

        for i in range(num_runs):
            print(f"   Run {i+1}/{num_runs}...", end=" ")
            start_time = time.time()

            try:
                blueprint_yaml = natural_language_to_yaml(description)
                blueprints.append(blueprint_yaml)
                generation_time = time.time() - start_time
                generation_times.append(generation_time)
                print(f"✓ ({generation_time:.2f}s)")
            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        # Calculate consistency metrics
        consistency_scores = []
        for i in range(len(blueprints)):
            for j in range(i + 1, len(blueprints)):
                similarity = self._calculate_similarity(blueprints[i], blueprints[j])
                consistency_scores.append(similarity)

        avg_consistency = (
            sum(consistency_scores) / len(consistency_scores)
            if consistency_scores
            else 0
        )
        avg_time = sum(generation_times) / len(generation_times) if generation_times else 0

        result = {
            "description": description,
            "num_runs": num_runs,
            "successful_runs": len(blueprints),
            "avg_consistency_score": avg_consistency,
            "min_consistency": min(consistency_scores) if consistency_scores else 0,
            "max_consistency": max(consistency_scores) if consistency_scores else 0,
            "avg_generation_time": avg_time,
            "blueprints": blueprints,
        }

        self.results["consistency_tests"].append(result)
        return result

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        return SequenceMatcher(None, text1, text2).ratio()

    def measure_yaml_quality(self, blueprint_yaml: str) -> Dict[str, Any]:
        """
        Measure quality metrics of generated YAML
        """
        try:
            data = yaml.safe_load(blueprint_yaml)

            metrics = {
                "valid_yaml": True,
                "has_root": "root" in data,
                "has_modules": "modules" in data,
                "num_modules": len(data.get("modules", [])),
                "total_fields": 0,
                "total_relations": 0,
                "has_validation": False,
            }

            # Count fields and relations
            for module in data.get("modules", []):
                entity = module.get("entity", {})
                fields = entity.get("fields", [])
                relations = entity.get("relations", [])

                metrics["total_fields"] += len(fields)
                metrics["total_relations"] += len(relations)

                # Check if any field has validation
                for field in fields:
                    if "validation" in field:
                        metrics["has_validation"] = True

            return metrics

        except yaml.YAMLError:
            return {"valid_yaml": False}

    def measure_code_generation_performance(
        self, blueprint_file: str, project_dir: str
    ) -> Dict[str, Any]:
        """
        Measure code generation performance
        """
        print(f"\n⚡ Measuring code generation performance...")

        start_time = time.time()

        try:
            # Run code generation
            from dsl.generate import main as dsl_generate_main

            dsl_generate_main(blueprint_file, project_dir)

            generation_time = time.time() - start_time

            # Count generated files
            src_dir = Path(project_dir) / "src"
            if src_dir.exists():
                ts_files = list(src_dir.rglob("*.ts"))
                num_files = len(ts_files)
                total_lines = sum(
                    len(f.read_text().splitlines()) for f in ts_files if f.is_file()
                )
            else:
                num_files = 0
                total_lines = 0

            result = {
                "generation_time": generation_time,
                "num_files_generated": num_files,
                "total_lines_of_code": total_lines,
                "lines_per_second": total_lines / generation_time if generation_time > 0 else 0,
            }

            print(f"   ✓ Generated {num_files} files ({total_lines} lines) in {generation_time:.2f}s")

            self.results["performance_tests"].append(result)
            return result

        except Exception as e:
            print(f"   ✗ Error: {e}")
            return {"error": str(e)}

    def run_comprehensive_test_suite(self):
        """
        Run a comprehensive suite of tests
        """
        print("=" * 70)
        print("🔬 COMPREHENSIVE METRICS COLLECTION")
        print("=" * 70)

        # Test cases with varying complexity
        test_cases = [
            {
                "name": "Simple Blog",
                "description": "Create a blog with users and posts",
                "complexity": "low",
            },
            {
                "name": "E-Commerce",
                "description": "Create an e-commerce system with products, customers, orders, and order items",
                "complexity": "medium",
            },
            {
                "name": "Social Network",
                "description": "Create a social network with users, posts, comments, likes, and friendships",
                "complexity": "high",
            },
            {
                "name": "Task Manager",
                "description": "Create a task management system with users, projects, tasks, and subtasks",
                "complexity": "medium",
            },
        ]

        for i, test_case in enumerate(test_cases):
            print(f"\n{'='*70}")
            print(f"Test Case {i+1}/{len(test_cases)}: {test_case['name']} ({test_case['complexity']} complexity)")
            print(f"{'='*70}")

            # Measure consistency
            consistency_result = self.measure_consistency(
                test_case["description"], num_runs=5
            )

            # Measure YAML quality on first blueprint
            if consistency_result["blueprints"]:
                quality_metrics = self.measure_yaml_quality(
                    consistency_result["blueprints"][0]
                )
                quality_metrics["test_case"] = test_case["name"]
                quality_metrics["complexity"] = test_case["complexity"]
                self.results["quality_metrics"].append(quality_metrics)

        # Save results
        self.save_results()

    def save_results(self):
        """Save metrics results to JSON file"""
        output_file = self.output_dir / "metrics_results.json"

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n✅ Metrics saved to: {output_file}")
        return output_file

    def generate_summary_report(self) -> str:
        """Generate a human-readable summary report"""
        report = []
        report.append("=" * 70)
        report.append("📊 METRICS SUMMARY REPORT")
        report.append("=" * 70)
        report.append("")

        # Consistency Summary
        if self.results["consistency_tests"]:
            report.append("## Consistency Metrics")
            report.append("")

            avg_scores = [
                test["avg_consistency_score"]
                for test in self.results["consistency_tests"]
            ]
            overall_avg = sum(avg_scores) / len(avg_scores)

            report.append(f"Overall Average Consistency: {overall_avg*100:.2f}%")
            report.append("")

            for test in self.results["consistency_tests"]:
                report.append(f"- {test['description'][:50]}...")
                report.append(f"  Consistency: {test['avg_consistency_score']*100:.2f}%")
                report.append(f"  Avg Time: {test['avg_generation_time']:.2f}s")
                report.append("")

        # Quality Summary
        if self.results["quality_metrics"]:
            report.append("## Quality Metrics")
            report.append("")

            for metric in self.results["quality_metrics"]:
                report.append(f"- {metric.get('test_case', 'Unknown')}")
                report.append(f"  Modules: {metric.get('num_modules', 0)}")
                report.append(f"  Fields: {metric.get('total_fields', 0)}")
                report.append(f"  Relations: {metric.get('total_relations', 0)}")
                report.append("")

        report_text = "\n".join(report)
        print(report_text)

        # Save report
        report_file = self.output_dir / "metrics_summary.txt"
        with open(report_file, "w") as f:
            f.write(report_text)

        return report_text


def main():
    parser = argparse.ArgumentParser(
        description="Collect metrics on DSL-based code generation"
    )

    parser.add_argument(
        "--output",
        "-o",
        default="./metrics_output",
        help="Output directory for metrics data",
    )

    parser.add_argument(
        "--runs",
        "-r",
        type=int,
        default=5,
        help="Number of runs per test case for consistency measurement",
    )

    parser.add_argument(
        "--test",
        "-t",
        help="Run a single test with custom description",
    )

    args = parser.parse_args()

    collector = MetricsCollector(output_dir=args.output)

    if args.test:
        # Single test mode
        result = collector.measure_consistency(args.test, num_runs=args.runs)
        collector.save_results()
        collector.generate_summary_report()
    else:
        # Full test suite
        collector.run_comprehensive_test_suite()
        collector.generate_summary_report()


if __name__ == "__main__":
    main()
