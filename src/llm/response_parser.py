"""Helpers for cleaning LLM responses and repairing malformed JSON."""

import json
import re
from json import JSONDecodeError
from typing import Any

from src.shared.exceptions import JSONParseException

CODE_BLOCK_PATTERN = re.compile(r"```(?:\w+)?\s*(.*?)\s*```", re.DOTALL)
THINKING_MARKERS = ["'type': 'thinking'", '"type": "thinking"']
TEXT_EXTRACTION_PATTERNS = [
    re.compile(r"'text':\s*'([^']*(?:\\.[^']*)*)'", re.DOTALL),
    re.compile(r'"text":\s*"([^"]*(?:\\.[^"]*)*)"', re.DOTALL),
]
THINKING_ESCAPE_REPLACEMENTS = {
    "\\n": "\n",
    "\\t": "\t",
    "\\'": "'",
    '\\"': '"',
}
CONTROL_CHARACTER_REPLACEMENTS = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
JSON_CLOSING_SUFFIXES = ['"}', '"\n}', '",\n}', '"}}}', '"\n}\n}', "}", "\n}", '"\n}', '"}]}']
JSON_START_PATTERN = re.compile(r'\{?\s*"')
LAST_COMPLETE_ENTRY_PATTERN = re.compile(r'"[^"]+":\s*"[^"]*"[,\n]')


def clean_llm_response(content: str) -> str:
    r"""Remove markdown wrappers and thinking blocks from an LLM response."""
    content = content.strip()

    match = CODE_BLOCK_PATTERN.search(content)

    if match:
        content = match.group(1).strip()

    if _contains_thinking_marker(content):
        content = _remove_thinking_blocks(content)

    return content


def _contains_thinking_marker(content: str) -> bool:
    """Check whether content includes a provider thinking block marker."""
    return any(marker in content for marker in THINKING_MARKERS)


def _remove_thinking_blocks(content: str) -> str:
    """Extract usable text from a response that includes thinking blocks."""
    content = content.strip()

    if not content.startswith("[{"):
        return content

    if not _contains_thinking_marker(content):
        return content

    for pattern in TEXT_EXTRACTION_PATTERNS:
        match = pattern.search(content)
        if match:
            return _unescape_thinking_text(match.group(1))

    return content


def _unescape_thinking_text(content: str) -> str:
    """Unescape common sequences in extracted thinking-block text."""
    for source, target in THINKING_ESCAPE_REPLACEMENTS.items():
        content = content.replace(source, target)
    return content


def _fix_json_escaping(content: str) -> str:
    """Normalize invalid escape handling inside LLM-generated JSON."""
    result = []
    in_string = False
    escape_next = False

    for char in content:
        if escape_next:
            result.append('"' if char == "'" else char)
            escape_next = False
            continue

        if char == "\\":
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            continue

        if in_string and char in CONTROL_CHARACTER_REPLACEMENTS:
            result.append(CONTROL_CHARACTER_REPLACEMENTS[char])
            continue

        result.append(char)

    return "".join(result)


def _try_parse_with_closing(content: str, closing: str) -> dict[str, Any] | None:
    """Try parsing JSON after appending one candidate closing suffix."""
    try:
        return json.loads(content + closing)
    except JSONDecodeError:
        return None


def _fix_literal_newlines(content: str) -> str:
    """Convert top-level literal newline escapes into real newlines."""
    result = []
    i = 0
    in_string = False
    prev_was_backslash = False

    while i < len(content):
        char = content[i]

        if prev_was_backslash:
            if char == "n" and not in_string:
                result[-1] = "\n"
            elif char == "'":
                result[-1] = "'"
            else:
                result.append(char)
            prev_was_backslash = False
            i += 1
            continue

        if char == "\\":
            prev_was_backslash = True
            result.append(char)
            i += 1
            continue

        if char == '"':
            in_string = not in_string

        result.append(char)
        i += 1

    return "".join(result)


def _apply_repair_strategies(content: str) -> dict[str, Any] | None:
    """Run the standard sequence of JSON repair strategies."""
    strategies = [_parse_with_escaped_json, _parse_with_literal_newlines]
    strategies.extend(_build_closing_repair_strategies())
    strategies.append(_extract_and_repair_json)

    for strategy in strategies:
        try:
            result = strategy(content)
            if result is not None:
                return result
        except (JSONDecodeError, Exception):
            continue

    return None


def _parse_with_escaped_json(content: str) -> dict[str, Any]:
    """Parse JSON after normalizing escape sequences."""
    return json.loads(_fix_json_escaping(content))


def _parse_with_literal_newlines(content: str) -> dict[str, Any]:
    """Parse JSON after repairing literal newline sequences."""
    return json.loads(_fix_literal_newlines(content))


def _build_closing_repair_strategies() -> list:
    """Create the standard closing-suffix repair attempts."""
    escaped_suffixes = {'"}', '"\n}', '",\n}', '"}}}', '"\n}\n}', '"}]}'}
    strategies = []
    for suffix in JSON_CLOSING_SUFFIXES:
        if suffix in escaped_suffixes:
            strategies.append(
                lambda content, current_suffix=suffix: _try_parse_with_closing(
                    _fix_json_escaping(content),
                    current_suffix,
                )
            )
        else:
            strategies.append(
                lambda content, current_suffix=suffix: _try_parse_with_closing(
                    content,
                    current_suffix,
                )
            )
    return strategies


def _extract_and_repair_json(content: str) -> dict[str, Any] | None:
    """Repair truncated JSON by normalizing and progressively trimming it."""
    content = _fix_json_escaping(content)

    if not content.strip().startswith("{"):
        content = _ensure_json_has_opening_brace(content)

    if not content.strip().endswith("}"):
        content = content + "}"

    try:
        return json.loads(content)
    except JSONDecodeError:
        pass

    repaired = _repair_by_truncating_lines(content)
    if repaired is not None:
        return repaired

    matches = list(LAST_COMPLETE_ENTRY_PATTERN.finditer(content))
    if matches:
        last_complete = matches[-1].end()
        truncated = content[:last_complete]
        truncated = _ensure_json_has_opening_brace(truncated)
        if not truncated.strip().endswith("}"):
            truncated = truncated + '"}'
        try:
            return json.loads(truncated)
        except JSONDecodeError:
            pass

    return None


def _ensure_json_has_opening_brace(content: str) -> str:
    """Add a leading opening brace when the JSON body starts mid-stream."""
    if content.strip().startswith("{"):
        return content

    if content.strip().startswith('"'):
        return "{" + content

    match = JSON_START_PATTERN.search(content)
    if match:
        return "{" + content[match.start() :]
    return content


def _repair_by_truncating_lines(content: str) -> dict[str, Any] | None:
    """Try parsing progressively shorter line-based truncations."""
    lines = content.split("\n")
    for index in range(len(lines), 0, -1):
        truncated = _normalize_json_fragment("\n".join(lines[:index]))
        try:
            return json.loads(truncated)
        except JSONDecodeError:
            continue
    return None


def _normalize_json_fragment(content: str) -> str:
    """Normalize a partial JSON fragment so it can be reparsed."""
    content = _ensure_json_has_opening_brace(content)
    if not content.strip().endswith("}"):
        content = content + "}"
    return content


def try_parse_json(content: str) -> dict[str, Any]:
    """Parse JSON and fall back to repair strategies when needed."""
    try:
        return json.loads(content)
    except JSONDecodeError as e:
        original_error = e

    repaired = _apply_repair_strategies(content)
    if repaired is not None:
        return repaired

    raise JSONParseException(
        f"Could not parse JSON even after attempting repairs. Original error: {original_error}",
        code="JSON001",
        context={
            "content_preview": content[:200],
            "content_length": len(content),
            "original_error": str(original_error),
        },
    )
