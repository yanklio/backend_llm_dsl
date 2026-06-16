"""Tests for LLM response parsing and JSON repair utilities."""

import pytest

from src.llm.response_parser import (
    _apply_repair_strategies,
    _build_closing_repair_strategies,
    _contains_thinking_marker,
    _ensure_json_has_opening_brace,
    _fix_json_escaping,
    _fix_literal_newlines,
    _normalize_json_fragment,
    _parse_with_escaped_json,
    _parse_with_literal_newlines,
    _remove_thinking_blocks,
    _repair_by_truncating_lines,
    _unescape_thinking_text,
    clean_llm_response,
    try_parse_json,
)
from src.shared.exceptions import JSONParseException


class TestCleanLlmResponse:
    """Tests for clean_llm_response()."""

    def test_normal_string_no_markdown(self):
        assert clean_llm_response("hello world") == "hello world"

    def test_string_stripped(self):
        assert clean_llm_response("  hello world  ") == "hello world"

    def test_markdown_json_block(self):
        result = clean_llm_response('```json\n{"key": "value"}\n```')
        assert result == '{"key": "value"}'

    def test_markdown_yaml_block(self):
        result = clean_llm_response("```yaml\nname: test\n```")
        assert result == "name: test"

    def test_markdown_block_no_lang(self):
        result = clean_llm_response("```\nplain content\n```")
        assert result == "plain content"

    def test_thinking_marker_extracted(self):
        content = """[{'type': 'thinking', 'text': 'hello\\nworld'}]"""
        result = clean_llm_response(content)
        assert result == "hello\nworld"

    def test_thinking_with_code_block(self):
        content = """```json\n[{'type': 'thinking', 'text': 'extracted'}]\n```"""
        result = clean_llm_response(content)
        assert result == "extracted"

    def test_only_whitespace(self):
        assert clean_llm_response("   ") == ""

    def test_empty_string(self):
        assert clean_llm_response("") == ""


class TestContainsThinkingMarker:
    """Tests for _contains_thinking_marker()."""

    def test_with_single_quote_marker(self):
        assert _contains_thinking_marker("'type': 'thinking'") is True

    def test_with_double_quote_marker(self):
        assert _contains_thinking_marker('"type": "thinking"') is True

    def test_without_marker(self):
        assert _contains_thinking_marker("hello world") is False

    def test_empty_string(self):
        assert _contains_thinking_marker("") is False

    def test_partial_marker_no_match(self):
        assert _contains_thinking_marker("'type': 'thinkin") is False


class TestRemoveThinkingBlocks:
    """Tests for _remove_thinking_blocks()."""

    def test_no_thinking_marker_returns_as_is(self):
        assert _remove_thinking_blocks("hello") == "hello"

    def test_not_starting_with_brace_bracket_returns_as_is(self):
        content = "plain text 'type': 'thinking'"
        assert _remove_thinking_blocks(content) == content

    def test_extracts_unescapes_text_from_single_quote_block(self):
        content = """[{'type': 'thinking', 'text': 'hello\\nworld\\ttest'}]"""
        result = _remove_thinking_blocks(content)
        assert result == "hello\nworld\ttest"

    def test_extracts_text_from_double_quote_block(self):
        content = '[{"type": "thinking", "text": "hello\\nworld"}]'
        result = _remove_thinking_blocks(content)
        assert result == "hello\nworld"

    def test_strips_whitespace(self):
        content = "  [{'type': 'thinking', 'text': 'hello'}]  "
        result = _remove_thinking_blocks(content)
        assert result == "hello"


class TestUnescapeThinkingText:
    """Tests for _unescape_thinking_text()."""

    def test_unescapes_newline(self):
        assert _unescape_thinking_text("hello\\nworld") == "hello\nworld"

    def test_unescapes_tab(self):
        assert _unescape_thinking_text("hello\\tworld") == "hello\tworld"

    def test_unescapes_single_quote(self):
        assert _unescape_thinking_text("it\\'s") == "it's"

    def test_unescapes_double_quote(self):
        assert _unescape_thinking_text('say\\"hello\\"') == 'say"hello"'

    def test_mixed_escapes(self):
        result = _unescape_thinking_text("line1\\nline2\\ttab\\'quote\\\"dq")
        assert result == "line1\nline2\ttab'quote\"dq"

    def test_no_escapes_unchanged(self):
        assert _unescape_thinking_text("hello") == "hello"


class TestFixJsonEscaping:
    """Tests for _fix_json_escaping()."""

    def test_normal_json_passes_through(self):
        content = '{"key": "value"}'
        assert _fix_json_escaping(content) == content

    def test_escaped_single_quote_becomes_double_quote(self):
        result = _fix_json_escaping("""{"key": "it\\'s"}""")
        assert result == """{"key": "it\\"s"}"""

    def test_control_chars_inside_strings_escaped(self):
        content = '{"key": "line1\nline2"}'
        result = _fix_json_escaping(content)
        assert result == '{"key": "line1\\nline2"}'

    def test_tab_inside_string_escaped(self):
        content = '{"key": "col1\tcol2"}'
        result = _fix_json_escaping(content)
        assert result == '{"key": "col1\\tcol2"}'

    def test_carriage_return_inside_string_escaped(self):
        content = '{"key": "line1\rline2"}'
        result = _fix_json_escaping(content)
        assert result == '{"key": "line1\\rline2"}'

    def test_plain_text_no_strings_unchanged(self):
        assert _fix_json_escaping("hello world") == "hello world"

    def test_backslash_escape_preserved(self):
        content = '{"path": "C:\\\\users\\\\me"}'
        result = _fix_json_escaping(content)
        assert result == content


class TestTryParseJson:
    """Tests for try_parse_json()."""

    def test_valid_json(self):
        assert try_parse_json('{"key": "value"}') == {"key": "value"}

    def test_valid_json_with_whitespace(self):
        assert try_parse_json('  {"key": "value"}  ') == {"key": "value"}

    def test_missing_closing_brace_repaired(self):
        result = try_parse_json('{"key": "value"')
        assert result == {"key": "value"}

    def test_missing_closing_brace_and_quote_repaired(self):
        result = try_parse_json('{"key": "value')
        assert result == {"key": "value"}

    def test_literal_newlines_in_values_repaired(self):
        content = '{"key": "line1\nline2"}'
        result = try_parse_json(content)
        assert result == {"key": "line1\nline2"}

    def test_escaped_single_quotes_repaired(self):
        content = """{"key": "it\\'s here"}"""
        result = try_parse_json(content)
        assert result == {"key": 'it"s here'}

    def test_truncated_multiline_repaired_by_line_truncation(self):
        content = '{"key": "value"\n "key2": "incomp'
        result = try_parse_json(content)
        assert result == {"key": "value"}

    def test_truncated_last_entry_fixed_by_closing_strategy(self):
        content = '{"a": "1", "b": "2", "c": "unfinis'
        result = try_parse_json(content)
        assert result == {"a": "1", "b": "2", "c": "unfinis"}

    def test_completely_invalid_raises_exception(self):
        with pytest.raises(JSONParseException) as exc_info:
            try_parse_json("not json at all")
        assert exc_info.value.code == "JSON001"
        assert "content_preview" in exc_info.value.context
        assert "content_length" in exc_info.value.context
        assert "original_error" in exc_info.value.context

    def test_empty_string_raises_exception(self):
        with pytest.raises(JSONParseException):
            try_parse_json("")

    def test_nested_object_repaired(self):
        result = try_parse_json('{"outer": {"inner": "value"}')
        assert result == {"outer": {"inner": "value"}}

    def test_array_content_repaired(self):
        result = try_parse_json('{"items": [1, 2, 3]')
        assert result == {"items": [1, 2, 3]}


class TestParseWithEscapedJson:
    """Tests for _parse_with_escaped_json()."""

    def test_parses_escaped_content(self):
        content = '{"key": "line1\\nline2"}'
        result = _parse_with_escaped_json(content)
        assert result == {"key": "line1\nline2"}

    def test_parses_with_single_quote_fix(self):
        content = '{"key": "it\\"s"}'
        result = _parse_with_escaped_json(content)
        assert result == {"key": 'it"s'}


class TestParseWithLiteralNewlines:
    """Tests for _parse_with_literal_newlines()."""

    def test_parses_with_backslash_n_outside_strings(self):
        content = '{"a": 1\\n, "b": 2}'
        result = _parse_with_literal_newlines(content)
        assert result == {"a": 1, "b": 2}

    def test_parses_simple_valid_json(self):
        result = _parse_with_literal_newlines('{"key": "value"}')
        assert result == {"key": "value"}


class TestRepairByTruncatingLines:
    """Tests for _repair_by_truncating_lines()."""

    def test_valid_json_returns_parsed(self):
        result = _repair_by_truncating_lines('{"key": "value"}')
        assert result == {"key": "value"}

    def test_garbage_last_line_truncated(self):
        content = '{"key": "value"}\ngarbage'
        result = _repair_by_truncating_lines(content)
        assert result == {"key": "value"}

    def test_multiline_repaired(self):
        content = '{\n"a": 1\n}\nextra'
        result = _repair_by_truncating_lines(content)
        assert result == {"a": 1}

    def test_entirely_invalid_returns_none(self):
        result = _repair_by_truncating_lines("{[broken")
        assert result is None


class TestNormalizeJsonFragment:
    """Tests for _normalize_json_fragment()."""

    def test_missing_opening_brace_added(self):
        result = _normalize_json_fragment('"key": "value"}')
        assert result == '{"key": "value"}'

    def test_missing_closing_brace_added(self):
        result = _normalize_json_fragment('{"key": "value"')
        assert result == '{"key": "value"}'

    def test_both_braces_present_unchanged(self):
        content = '{"key": "value"}'
        assert _normalize_json_fragment(content) == content

    def test_both_missing_added(self):
        result = _normalize_json_fragment('"key": "value"')
        assert result == '{"key": "value"}'


class TestEnsureJsonHasOpeningBrace:
    """Tests for _ensure_json_has_opening_brace()."""

    def test_starts_with_quote_adds_brace(self):
        result = _ensure_json_has_opening_brace('"key": "value"')
        assert result == '{"key": "value"'

    def test_already_has_brace_unchanged(self):
        content = '{"key": "value"}'
        assert _ensure_json_has_opening_brace(content) == content

    def test_starts_with_text_finds_first_quote(self):
        result = _ensure_json_has_opening_brace('prefix"key": "value"')
        assert result == '{"key": "value"'


class TestBuildClosingRepairStrategies:
    """Tests for _build_closing_repair_strategies()."""

    def test_returns_list_of_callables(self):
        strategies = _build_closing_repair_strategies()
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        for s in strategies:
            assert callable(s)


class TestApplyRepairStrategies:
    """Tests for _apply_repair_strategies()."""

    def test_fails_all_strategies_returns_none(self):
        result = _apply_repair_strategies("complete garbage")
        assert result is None

    def test_repaired_returns_parsed_dict(self):
        result = _apply_repair_strategies('{"key": "value"')
        assert result == {"key": "value"}

    def test_repaired_with_control_chars(self):
        content = '{"key": "line1\nline2"}'
        result = _apply_repair_strategies(content)
        assert result == {"key": "line1\nline2"}


class TestFixLiteralNewlines:
    """Tests for _fix_literal_newlines()."""

    def test_backslash_n_outside_strings_converted(self):
        result = _fix_literal_newlines("{a\\nb}")
        assert result == "{a\nb}"

    def test_backslash_n_inside_strings_unchanged(self):
        content = '{"key": "value\\nwith newline"}'
        result = _fix_literal_newlines(content)
        assert result == content

    def test_regular_newlines_unchanged(self):
        content = '{"key": "line1\nline2"}'
        result = _fix_literal_newlines(content)
        assert result == content

    def test_backslash_single_quote_outside_strings_converted(self):
        result = _fix_literal_newlines("""{a\\'b}""")
        assert result == "{a'b}"

    def test_mixed_outside_and_inside(self):
        content = '{"key": "val\\n"}\\n{"key2": "val2"}'
        result = _fix_literal_newlines(content)
        assert '{"key": "val\\n"}' in result
        assert "\n" in result


class TestJSONParseException:
    """Tests for JSONParseException raised by try_parse_json()."""

    def test_exception_attributes(self):
        with pytest.raises(JSONParseException) as exc_info:
            try_parse_json("invalid{{{")
        assert exc_info.value.code == "JSON001"
        assert "content_preview" in exc_info.value.context
        assert exc_info.value.context["content_length"] == 10

    def test_exception_inheritance(self):
        with pytest.raises(JSONParseException):
            try_parse_json("garbage")
