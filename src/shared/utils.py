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
    r"""Clean LLM response by removing markdown code blocks.

    Supports json, yaml, and generic code blocks. Extracts content
    between ``` markers if present.

    Args:
        content: Raw LLM response string

    Returns:
        Cleaned content with markdown removed

    Example:
        >>> clean_llm_response("```json\\n{\"key\": \"value\"}\\n```")
        '{"key": "value"}'
    """
    content = content.strip()

    pattern = r"```(?:\w+)?\s*(.*?)\s*```"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        content = match.group(1).strip()

    return content


def _fix_json_escaping(content: str) -> str:
    """Attempt to fix common JSON escaping issues in LLM-generated content.

    Handles unescaped newlines, carriage returns, and tabs within string values.

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
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"\n}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '",\n}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"}}}'),
        lambda c: _try_parse_with_closing(_fix_json_escaping(c), '"\n}\n}'),
        lambda c: _try_parse_with_closing(c, "}"),
        lambda c: _try_parse_with_closing(c, "\n}"),
        lambda c: _try_parse_with_closing(c, '"\n}'),
    ]

    for strategy in strategies:
        try:
            return strategy(content)
        except (JSONDecodeError, Exception):
            continue

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
