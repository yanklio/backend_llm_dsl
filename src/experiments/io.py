"""I/O helpers for experiment execution and persistence."""

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from .paths import DEBUG_LOG_FILE, RESULTS_FILE, TEST_CASES_FILE


class SuppressOutput:
    """Temporarily redirect stdout/stderr to the debug log."""

    def __enter__(self) -> None:
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._log_file = open(DEBUG_LOG_FILE, "a")
        sys.stdout = self._log_file
        sys.stderr = self._log_file

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        if self._log_file:
            self._log_file.close()


def load_test_cases() -> dict[str, Any]:
    """Load benchmark case definitions."""
    with open(TEST_CASES_FILE) as file_handle:
        return yaml.safe_load(file_handle)


def load_results(results_file: Path = RESULTS_FILE) -> list[dict[str, Any]]:
    """Load persisted experiment results if they exist."""
    if not results_file.exists():
        return []

    try:
        with open(results_file) as file_handle:
            return json.load(file_handle)
    except Exception:
        return []


def save_json(path: Path, payload: Any) -> None:
    """Persist a JSON payload to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as file_handle:
        json.dump(payload, file_handle, indent=2)


def save_results(results: list[dict[str, Any]], results_file: Path = RESULTS_FILE) -> None:
    """Persist experiment results to disk."""
    try:
        save_json(results_file, results)
    except Exception as exc:
        print(f"Failed to save results: {exc}")
