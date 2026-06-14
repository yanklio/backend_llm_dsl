"""Smoke tests for experiment paths module."""

from pathlib import Path

from src.experiments.paths import (
    ANALYTICS_DIR,
    BASE_NEST_PROJECT_DIR,
    DEBUG_LOG_FILE,
    NEST_PROJECT_DIR,
    PROJECT_ROOT,
    RESULTS_DIR,
    RUNS_DIR,
    TEST_CASES_DIR,
    TEST_CASES_FILE,
    blueprint_path_for,
)


class TestPathsConstants:
    """Verify that all path constants resolve to valid Paths."""

    def test_project_root_is_path(self):
        assert isinstance(PROJECT_ROOT, Path)
        assert PROJECT_ROOT.exists()

    def test_results_dir_is_path(self):
        assert isinstance(RESULTS_DIR, Path)

    def test_test_cases_file_is_path(self):
        assert isinstance(TEST_CASES_FILE, Path)

    def test_nest_project_dir_is_path(self):
        assert isinstance(NEST_PROJECT_DIR, Path)

    def test_analytics_dir_is_path(self):
        assert isinstance(ANALYTICS_DIR, Path)

    def test_runs_dir_is_path(self):
        assert isinstance(RUNS_DIR, Path)

    def test_debug_log_file_is_path(self):
        assert isinstance(DEBUG_LOG_FILE, Path)

    def test_base_nest_project_dir_is_path(self):
        assert isinstance(BASE_NEST_PROJECT_DIR, Path)

    def test_test_cases_dir_is_path(self):
        assert isinstance(TEST_CASES_DIR, Path)


class TestBlueprintPathFor:
    """Verify blueprint_path_for builds correct paths."""

    def test_basic_path(self):
        result = blueprint_path_for("TEST_CASE_1")
        assert isinstance(result, Path)
        assert "TEST_CASE_1" in str(result)
        assert result.suffix == ".yaml"

    def test_path_with_suffix(self):
        result = blueprint_path_for("TEST_CASE_1", "_blueprint")
        assert "_blueprint" in result.stem
