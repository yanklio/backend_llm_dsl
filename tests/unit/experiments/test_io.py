"""Smoke tests for experiment I/O module."""

import json

from src.experiments.io import (
    SuppressOutput,
    load_results,
    save_json,
    save_results,
)


class TestSuppressOutput:
    """Verify SuppressOutput context manager."""

    def test_context_manager_restores_streams(self):
        import sys

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        with SuppressOutput():
            assert sys.stdout is not original_stdout
            assert sys.stderr is not original_stderr

        assert sys.stdout is original_stdout
        assert sys.stderr is original_stderr


class TestSaveAndLoad:
    """Verify JSON persistence helpers."""

    def test_save_json(self, temp_dir):
        path = temp_dir / "test.json"
        save_json(path, {"key": "value"})
        assert path.exists()
        assert json.loads(path.read_text()) == {"key": "value"}

    def test_save_json_creates_parents(self, temp_dir):
        path = temp_dir / "nested" / "sub" / "test.json"
        save_json(path, [1, 2, 3])
        assert path.exists()

    def test_save_results(self, temp_dir):
        results_path = temp_dir / "results.json"
        data = [{"id": 1}, {"id": 2}]
        save_results(data, results_path)
        assert results_path.exists()

    def test_load_results_nonexistent_file(self, temp_dir):
        path = temp_dir / "nonexistent.json"
        assert load_results(path) == []

    def test_load_results_empty_file(self, temp_dir):
        path = temp_dir / "empty.json"
        path.write_text("")
        assert load_results(path) == []

    def test_load_results_malformed_file(self, temp_dir):
        path = temp_dir / "bad.json"
        path.write_text("not json")
        assert load_results(path) == []
