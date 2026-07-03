"""Tests for LLM file writer helpers."""

import json
from unittest.mock import patch

from packages.llm_providers.generators.file_writer import (
    _has_many_literal_escapes,
    prepare_file_content,
    save_generated_files,
)


class TestHasManyLiteralEscapes:
    """Tests for _has_many_literal_escapes function."""

    def test_detects_literal_escapes(self):
        content = "hello\\nworld\\nfoo"
        assert _has_many_literal_escapes(content) is True

    def test_returns_false_for_normal_newlines(self):
        content = "hello\nworld\nfoo"
        assert _has_many_literal_escapes(content) is False

    def test_returns_false_when_literal_not_dominant(self):
        content = "hello\\nworld\nfoo"
        assert _has_many_literal_escapes(content) is False

    def test_returns_false_for_empty_string(self):
        assert _has_many_literal_escapes("") is False

    def test_returns_false_for_no_backslash_n(self):
        content = "plain text"
        assert _has_many_literal_escapes(content) is False


class TestPrepareFileContent:
    """Tests for prepare_file_content function."""

    def test_dict_returns_json_string(self):
        result = prepare_file_content({"key": "value"}, "test.json")
        assert json.loads(result) == {"key": "value"}

    def test_list_returns_json_string(self):
        result = prepare_file_content([1, 2, 3], "test.json")
        assert json.loads(result) == [1, 2, 3]

    def test_normal_string_returns_as_is(self):
        result = prepare_file_content("console.log('hello');", "file.ts")
        assert result == "console.log('hello');"

    def test_escaped_string_is_unescaped(self):
        content = "line1\\nline2\\nline3"
        with patch("packages.llm_providers.generators.file_writer.logger"):
            result = prepare_file_content(content, "file.ts")
        assert result == "line1\nline2\nline3"

    def test_empty_string_returns_empty(self):
        assert prepare_file_content("", "file.ts") == ""


class TestSaveGeneratedFiles:
    """Tests for save_generated_files function."""

    def test_saves_multiple_files(self, temp_dir):
        files = {
            "hello.txt": "world",
            "data.json": json.dumps({"nested": True}),
        }
        count = save_generated_files(files, str(temp_dir))
        assert count == 2
        assert (temp_dir / "hello.txt").read_text() == "world"
        assert (temp_dir / "data.json").read_text() == json.dumps({"nested": True})

    def test_creates_nested_directories(self, temp_dir):
        files = {"src/module/file.ts": "content"}
        count = save_generated_files(files, str(temp_dir))
        assert count == 1
        assert (temp_dir / "src/module/file.ts").read_text() == "content"

    def test_returns_zero_for_empty_dict(self, temp_dir):
        count = save_generated_files({}, str(temp_dir))
        assert count == 0

    def test_partial_failure_still_counts_successes(self, temp_dir):
        files = {"ok.txt": "good", "bad.txt": None}
        count = save_generated_files(files, str(temp_dir))
        assert count == 1
        assert (temp_dir / "ok.txt").read_text() == "good"
