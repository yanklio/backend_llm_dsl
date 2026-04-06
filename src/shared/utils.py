"""Utility functions for cleaning and parsing LLM responses.

Provides functions for cleaning markdown from LLM responses and parsing
potentially malformed JSON with repair attempts.
"""

import re
from typing import Any


def clean_llm_response(content: str) -> str:
    """Clean LLM response by removing markdown code blocks.

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

    # regex for ```type ... ```
    # non-greedy match for content
    pattern = r"```(?:\w+)?\s*(.*?)\s*```"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        content = match.group(1).strip()

    return content


import json
from json import JSONDecodeError

from src.shared.exceptions import JSONParseException


def try_parse_json(content: str) -> dict[str, Any]:
    """Try to parse JSON, attempting to fix common LLM errors.

    Attempts multiple repair strategies for malformed JSON:
    1. Standard JSON parsing
    2. Fix unescaped control characters (newlines, tabs, etc.)
    3. Add missing closing braces/brackets
    4. Fix trailing commas

    Args:
        content: JSON string to parse

    Returns:
        Parsed JSON as a dictionary

    Raises:
        JSONParseException: If JSON cannot be parsed after all repair attempts
    """
    # First, try standard parsing
    try:
        return json.loads(content)
    except JSONDecodeError as e:
        original_error = e

    # Try to fix unescaped newlines and control characters FIRST
    # This is the most common issue where LLMs put literal newlines in JSON strings
    try:
        fixed_content = _fix_json_escaping(content)
        return json.loads(fixed_content)
    except (JSONDecodeError, Exception) as e:
        # Save this error for later
        fixed_error = e

    # Now try various truncation fixes on the escaped content
    try:
        fixed_content = _fix_json_escaping(content)

        closing_attempts = [
            '"}',  # Close string and object
            '"\n}',  # Close string with newline and object
            '",\n}',  # Close string with comma and object
            '"}}}',  # Close multiple nested objects
            '"\n}\n}',  # Close nested with newlines
        ]

        for closing in closing_attempts:
            try:
                return json.loads(fixed_content + closing)
            except JSONDecodeError:
                continue
    except Exception:
        pass

    # Try simple truncation fixes on original content
    try:
        return json.loads(content + "}")
    except JSONDecodeError:
        pass

    try:
        return json.loads(content + "\n}")
    except JSONDecodeError:
        pass

    try:
        return json.loads(content + '"\n}')
    except JSONDecodeError:
        pass

    # If all else fails, raise a descriptive error with context
    raise JSONParseException(
        f"Could not parse JSON even after attempting repairs. Original error: {original_error}",
        code="JSON001",
        context={
            "content_preview": content[:200],
            "content_length": len(content),
            "original_error": str(original_error)
        }
    )


def _fix_json_escaping(content: str) -> str:
    """Attempt to fix common JSON escaping issues in LLM-generated content.

    Handles:
    - Unescaped newlines (\\n)
    - Unescaped carriage returns (\\r)
    - Unescaped tabs (\\t)

    Args:
        content: JSON string with potential escaping issues

    Returns:
        JSON string with control characters properly escaped

    Note:
        This is a heuristic approach and may not work for all edge cases.
    """
    # This is a heuristic approach - it may not work for all cases
    # The strategy is to find string values and escape control characters within them

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
            # Escape control characters within strings
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
