"""Shared filesystem paths for experiment workflows."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = PROJECT_ROOT / "tests"
RESULTS_DIR = PROJECT_ROOT / "results"
ANALYTICS_DIR = RESULTS_DIR / "analytics"
TEST_CASES_FILE = RESULTS_DIR / "test_cases.yaml"
TEST_CASES_DIR = RESULTS_DIR / "generated_blueprints"
RESULTS_FILE = RESULTS_DIR / "test_results.json"
RUNS_DIR = RESULTS_DIR / "runs"
DEBUG_LOG_FILE = RESULTS_DIR / "experiments_debug.log"
NEST_PROJECT_DIR = PROJECT_ROOT / "nest_project"
BASE_NEST_PROJECT_DIR = RESULTS_DIR / "base_nest_project"


def blueprint_path_for(test_case_name: str, suffix: str = "") -> Path:
    """Build the blueprint path for a given test case."""
    return TEST_CASES_DIR / "dsl_llm" / f"{test_case_name}{suffix}.yaml"
