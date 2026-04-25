"""Utility functions for cleaning and parsing LLM responses.

Provides functions for cleaning markdown from LLM responses and parsing
potentially malformed JSON with repair attempts.
"""

import json
import re
from json import JSONDecodeError
from typing import Any

from src.shared.exceptions import JSONParseException


def clean_llm_response(content: str) -> str:
    r"""Clean LLM response by removing markdown code blocks and thinking blocks.

    Supports json, yaml, and generic code blocks. Extracts content
    between ``` markers if present. Also removes thinking blocks.

    Args:
        content: Raw LLM response string

    Returns:
        Cleaned content with markdown and thinking blocks removed

    Example:
        >>> clean_llm_response("```json\n{\"key\": \"value\"}\n```")
        '{"key": "value"}'
    """
    content = content.strip()

    pattern = r"```(?:\w+)?\s*(.*?)\s*```"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        content = match.group(1).strip()

    # Only remove thinking blocks if they exist
    if "'type': 'thinking'" in content or '"type": "thinking"' in content:
        content = _remove_thinking_blocks(content)

    return content


def _remove_thinking_blocks(content: str) -> str:
    """Remove thinking blocks from JSON content.

    Gemini returns thinking blocks like:
    [{'type': 'thinking', 'thinking': '...'}, {'type': 'text', 'text': 'yaml...'}]

    This function extracts the actual content after the thinking blocks.

    Args:
        content: Content that may contain thinking blocks

    Returns:
        Content with thinking blocks removed
    """
    content = content.strip()

    # Only handle if it looks like a thinking block array at the start
    if not content.startswith("[{"):
        return content

    # Check if this is a thinking block response
    if "'type': 'thinking'" not in content and '"type": "thinking"' not in content:
        return content

    # Pattern: [{'type': 'thinking', ...}, {'type': 'text', 'text': 'content...'}]
    # We need to find the text field and extract its value

    # Look for the text field value
    # The content after thinking blocks is in the 'text' or "text" field
    patterns = [
        r"'text':\s*'([^']*(?:\\.[^']*)*)'",  # single quoted
        r'"text":\s*"([^"]*(?:\\.[^"]*)*)"',  # double quoted
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            extracted = match.group(1)
            # Unescape common escape sequences
            extracted = extracted.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'").replace('\\"', '"')
            return extracted

    return content


def _fix_json_escaping(content: str) -> str:
    """Attempt to fix common JSON escaping issues in LLM-generated content.

    Handles unescaped newlines, carriage returns, and tabs within string values.
    Also fixes escaped single quotes to escaped double quotes.

    Args:
        content: JSON string with potential escaping issues

    Returns:
        JSON string with control characters properly escaped
    """
    result = []
    in_string = False
    escape_next = False
    i = 0

    while i < len(content):
        char = content[i]

        if escape_next:
            if char == "'":
                result.append('"')
            else:
                result.append(char)
            escape_next = False
            i += 1
            continue

        if char == "\\":
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        if in_string:
            if char == "\n":
                result.append("\\n")
            elif char == "\r":
                result.append("\\r")
            elif char == "\t":
                result.append("\\t")
            else:
                result.append(char)
        else:
            result.append(char)

        i += 1

    return "".join(result)


def _try_parse_with_closing(content: str, closing: str) -> dict[str, Any] | None:
    """Try parsing JSON with a specific closing suffix.

    Args:
        content: JSON string to parse
        closing: String to append before parsing

    Returns:
        Parsed JSON or None if parsing fails
    """
    try:
        return json.loads(content + closing)
    except JSONDecodeError:
        return None


def _fix_literal_newlines(content: str) -> str:
    """Convert literal backslash-n at top level to actual newlines.

    Gemini sometimes returns JSON where top-level whitespace uses literal \\n
    instead of actual newlines or escaped \\n. Also fixes invalid escape sequences.

    Args:
        content: JSON string with literal \\n sequences

    Returns:
        Content with literal \\n converted to actual newlines and invalid escapes fixed
    """
    result = []
    i = 0
    in_string = False
    prev_was_backslash = False

    while i < len(content):
        char = content[i]

        if prev_was_backslash:
            # This char is escaped
            if char == "n" and not in_string:
                # \n outside string -> actual newline
                result[-1] = "\n"  # Replace the backslash
            elif char == "'":
                result[-1] = "'"  # \' -> ' (remove backslash)
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
    """Apply multiple JSON repair strategies in sequence.

    Strategies include: escaping fixes, closing bracket fixes, truncation fixes.

    Args:
        content: JSON string that may be malformed

    Returns:
        Parsed JSON or None if all repairs fail
    """
    strategies = [
        lambda c: json.loads(_fix_json_escaping(c)),
        lambda c: json.loads(_fix_literal_newlines(c)),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"\n}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '",\n}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"}}}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"\n}\n}'),
        lambda c: _try_parse_with_closing(c, "}"),
        lambda c: _try_parse_with_closing(c, "\n}"),
        lambda c: _try_parse_with_closing(c, '"\n}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"}]}'),
        lambda c: _extract_and_repair_json(c),
    ]

    for strategy in strategies:
        try:
            result = strategy(content)
            if result is not None:
                return result
        except (JSONDecodeError, Exception):
            continue

    return None


def _extract_and_repair_json(content: str) -> dict[str, Any] | None:
    """Extract valid JSON by truncating at the last complete entry.

    Handles cases where JSON is truncated mid-string (Gemini often truncates).

    Args:
        content: Potentially truncated JSON content

    Returns:
        Repaired JSON or None if repair fails
    """
    import re

    content = _fix_json_escaping(content)

    # Strategy 1: Fix missing opening brace
    if not content.strip().startswith("{"):
        # If content starts with a key, add opening brace
        if content.strip().startswith('"'):
            content = "{" + content
        else:
            # Find where JSON key starts
            match = re.search(r'\{?\s*"', content)
            if match:
                content = "{" + content[match.start():]

    # Strategy 2: Fix missing closing brace
    if not content.strip().endswith("}"):
        content = content + "}"

    # Try to parse with the fixes
    try:
        return json.loads(content)
    except JSONDecodeError:
        pass

    # Strategy 3: Find the last complete key-value pair
    lines = content.split("\n")
    for i in range(len(lines), 0, -1):
        truncated = "\n".join(lines[:i])
        if not truncated.strip().startswith("{"):
            truncated = "{" + truncated
        if not truncated.strip().endswith("}"):
            truncated = truncated + "}"
        try:
            return json.loads(truncated)
        except JSONDecodeError:
            continue

    # Strategy 4: Try to find the last complete JSON object entry
    matches = list(re.finditer(r'"[^"]+":\s*"[^"]*"[,\n]', content))
    if matches:
        last_complete = matches[-1].end()
        truncated = content[:last_complete]
        if not truncated.strip().startswith("{"):
            truncated = "{" + truncated
        if not truncated.strip().endswith("}"):
            truncated = truncated + '"}'
        try:
            return json.loads(truncated)
        except JSONDecodeError:
            pass

    return None


def try_parse_json(content: str) -> dict[str, Any]:
    """Try to parse JSON, attempting to fix common LLM errors.

    Attempts multiple repair strategies for malformed JSON:
    1. Standard JSON parsing
    2. Fix unescaped control characters (newlines, tabs, etc.)
    3. Add missing closing braces/brackets

    Args:
        content: JSON string to parse

    Returns:
        Parsed JSON as a dictionary

    Raises:
        JSONParseException: If JSON cannot be parsed after all repair attempts
    """
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
