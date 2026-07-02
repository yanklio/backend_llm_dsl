"""Tests for experiment result analysis module."""

import pytest

from apps.experiments.analysis import (
    _count_statuses,
    _group_results,
    _metric_means,
    _print_approach_summary,
    _print_average_metrics,
    _print_generation_errors,
    _print_tier_breakdown,
    analyze,
    main,
)

SAMPLE_RESULTS = [
    {
        "approach": "dsl",
        "tier": "simple",
        "test_case": "simple_blog",
        "generation": {
            "success": True,
            "metrics": {
                "total_time": 10.5,
                "llm_time": 8.0,
                "dsl_time": 2.5,
                "input_tokens": 500,
                "output_tokens": 200,
                "total_tokens": 700,
            },
        },
        "validation": {"overall_valid": True},
    },
    {
        "approach": "dsl",
        "tier": "medium",
        "test_case": "medium_ecommerce",
        "generation": {
            "success": True,
            "metrics": {
                "total_time": 20.0,
                "llm_time": 15.0,
                "dsl_time": 5.0,
                "input_tokens": 1000,
                "output_tokens": 400,
                "total_tokens": 1400,
            },
        },
        "validation": {"overall_valid": False},
    },
    {
        "approach": "raw",
        "tier": "simple",
        "test_case": "simple_blog_raw",
        "generation": {
            "success": False,
            "error": "API timeout",
            "metrics": {
                "total_time": 30.0,
                "llm_time": 30.0,
                "input_tokens": 600,
                "output_tokens": 0,
                "total_tokens": 600,
            },
        },
        "validation": {"overall_valid": False},
    },
    {
        "approach": "dsl",
        "tier": "simple",
        "test_case": "simple_api",
        "generation": {
            "success": True,
            "metrics": {
                "total_time": 5.0,
                "llm_time": 4.0,
                "dsl_time": 1.0,
                "input_tokens": 300,
                "output_tokens": 100,
                "total_tokens": 400,
            },
        },
        "validation": {"overall_valid": True},
    },
]

DSL_RESULTS = [r for r in SAMPLE_RESULTS if r["approach"] == "dsl"]
RAW_RESULTS = [r for r in SAMPLE_RESULTS if r["approach"] == "raw"]


class TestCountStatuses:
    """Verify _count_statuses result counting."""

    def test_mixed_results(self):
        passed, failed, errors = _count_statuses(SAMPLE_RESULTS)
        assert passed == 2
        assert failed == 1
        assert errors == 1

    def test_all_passed(self):
        results = [
            {"generation": {"success": True}, "validation": {"overall_valid": True}},
            {"generation": {"success": True}, "validation": {"overall_valid": True}},
        ]
        assert _count_statuses(results) == (2, 0, 0)

    def test_all_failed(self):
        results = [
            {"generation": {"success": True}, "validation": {"overall_valid": False}},
            {"generation": {"success": True}, "validation": {"overall_valid": False}},
        ]
        passed, failed, errors = _count_statuses(results)
        assert passed == 0
        assert failed == 2
        assert errors == 0

    def test_all_errors(self):
        results = [
            {"generation": {"success": False}},
            {"generation": {"success": False}},
        ]
        assert _count_statuses(results) == (0, 0, 2)

    def test_missing_validation_key(self):
        results = [{"generation": {"success": True}}]
        assert _count_statuses(results) == (0, 0, 0)

    def test_empty_list(self):
        assert _count_statuses([]) == (0, 0, 0)


class TestGroupResults:
    """Verify _group_results grouping logic."""

    def test_groups_by_approach(self):
        by_approach, _ = _group_results(SAMPLE_RESULTS)
        assert set(by_approach.keys()) == {"dsl", "raw"}
        assert len(by_approach["dsl"]) == 3
        assert len(by_approach["raw"]) == 1

    def test_groups_by_approach_and_tier(self):
        _, by_approach_tier = _group_results(SAMPLE_RESULTS)
        assert set(by_approach_tier["dsl"].keys()) == {"simple", "medium"}
        assert len(by_approach_tier["dsl"]["simple"]) == 2
        assert len(by_approach_tier["dsl"]["medium"]) == 1
        assert len(by_approach_tier["raw"]["simple"]) == 1

    def test_missing_tier_defaults_to_unknown(self):
        results = [{"approach": "test"}]
        _, by_approach_tier = _group_results(results)
        assert "unknown" in by_approach_tier["test"]

    def test_empty_list(self):
        by_approach, by_approach_tier = _group_results([])
        assert by_approach == {}
        assert by_approach_tier == {}


class TestMetricMeans:
    """Verify _metric_means calculations."""

    def test_correct_means_for_dsl(self):
        means = _metric_means(DSL_RESULTS)
        assert means["time"] == pytest.approx(11.8333, rel=1e-3)
        assert means["llm_time"] == 9.0
        assert means["dsl_time"] == pytest.approx(2.8333, rel=1e-3)
        assert means["input_tokens"] == 600.0
        assert means["output_tokens"] == pytest.approx(233.3333, rel=1e-3)
        assert means["total_tokens"] == pytest.approx(833.3333, rel=1e-3)

    def test_missing_dsl_time_defaults_to_zero(self):
        results = [
            {
                "generation": {
                    "success": True,
                    "metrics": {
                        "total_time": 10.0,
                        "llm_time": 10.0,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "total_tokens": 150,
                    },
                },
            }
        ]
        means = _metric_means(results)
        assert means["dsl_time"] == 0.0

    def test_single_result(self):
        means = _metric_means([DSL_RESULTS[0]])
        assert means["time"] == 10.5
        assert means["llm_time"] == 8.0
        assert means["input_tokens"] == 500.0


class TestPrintTierBreakdown:
    """Verify _print_tier_breakdown output."""

    def test_output_contains_tier_lines(self, capsys):
        _, by_approach_tier = _group_results(SAMPLE_RESULTS)
        _print_tier_breakdown("dsl", by_approach_tier)
        captured = capsys.readouterr()
        assert "Breakdown by Tier" in captured.out
        assert "Simple" in captured.out
        assert "Medium" in captured.out
        assert "2/2" in captured.out
        assert "0/1" in captured.out

    def test_empty_tier_no_crash(self, capsys):
        _, by_approach_tier = _group_results(SAMPLE_RESULTS)
        _print_tier_breakdown("nonexistent", by_approach_tier)
        captured = capsys.readouterr()
        assert "Breakdown by Tier" in captured.out


class TestPrintAverageMetrics:
    """Verify _print_average_metrics output."""

    def test_dsl_shows_dsl_exec(self, capsys):
        _print_average_metrics("dsl", DSL_RESULTS)
        captured = capsys.readouterr()
        assert "DSL Exec" in captured.out
        assert "Total" in captured.out

    def test_raw_hides_dsl_exec(self, capsys):
        _print_average_metrics("raw", RAW_RESULTS)
        captured = capsys.readouterr()
        assert "DSL Exec" not in captured.out
        assert "Total" in captured.out


class TestPrintGenerationErrors:
    """Verify _print_generation_errors output."""

    def test_with_errors(self, capsys):
        _print_generation_errors(RAW_RESULTS, 1)
        captured = capsys.readouterr()
        assert "Errors encountered" in captured.out
        assert "simple_blog_raw" in captured.out
        assert "API timeout" in captured.out

    def test_no_errors_prints_nothing(self, capsys):
        _print_generation_errors(DSL_RESULTS, 0)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestPrintApproachSummary:
    """Verify _print_approach_summary full output."""

    def test_dsl_summary(self, capsys):
        by_approach, by_approach_tier = _group_results(SAMPLE_RESULTS)
        _print_approach_summary("dsl", by_approach["dsl"], by_approach_tier)
        captured = capsys.readouterr()
        assert "DSL METHOD" in captured.out
        assert "Overall Success Rate" in captured.out
        assert "2 PASS" in captured.out
        assert "1 FAIL" in captured.out
        assert "Averages" in captured.out
        assert "Breakdown by Tier" in captured.out

    def test_raw_summary(self, capsys):
        by_approach, by_approach_tier = _group_results(SAMPLE_RESULTS)
        _print_approach_summary("raw", by_approach["raw"], by_approach_tier)
        captured = capsys.readouterr()
        assert "RAW METHOD" in captured.out
        assert "0 PASS" in captured.out
        assert "1 ERR" in captured.out
        assert "Averages" in captured.out
        assert "API timeout" in captured.out


class TestAnalyze:
    """Verify analyze entry point."""

    def test_with_results(self, capsys, monkeypatch):
        monkeypatch.setattr("apps.experiments.analysis.load_results", lambda _: SAMPLE_RESULTS)
        analyze()
        captured = capsys.readouterr()
        assert "Analysis of 4 experiments" in captured.out
        assert "DSL METHOD" in captured.out
        assert "RAW METHOD" in captured.out

    def test_empty_results(self, capsys, monkeypatch):
        monkeypatch.setattr("apps.experiments.analysis.load_results", lambda _: [])
        analyze()
        captured = capsys.readouterr()
        assert "No results found" in captured.out

    def test_passes_results_file_to_load_results(self, monkeypatch):
        from pathlib import Path

        captured_path = None

        def mock_load(path):
            nonlocal captured_path
            captured_path = path
            return []

        monkeypatch.setattr("apps.experiments.analysis.load_results", mock_load)
        custom_path = Path("/custom/results.json")
        analyze(custom_path)
        assert captured_path == custom_path


class TestMain:
    """Verify main CLI entry point."""

    def test_argparse_custom_path(self, monkeypatch):
        captured = []

        def mock_analyze(path):
            captured.append(path)

        monkeypatch.setattr("apps.experiments.analysis.analyze", mock_analyze)
        monkeypatch.setattr("sys.argv", ["analysis.py", "--results", "/tmp/test.json"])
        main()
        assert len(captured) == 1
        assert str(captured[0]) == "/tmp/test.json"

    def test_argparse_default_path(self, monkeypatch):
        captured = []

        def mock_analyze(path):
            captured.append(path)

        monkeypatch.setattr("apps.experiments.analysis.analyze", mock_analyze)
        monkeypatch.setattr("sys.argv", ["analysis.py"])
        main()
        assert len(captured) == 1
