
import re

def clean_llm_response(content: str) -> str:
    """
    Clean LLM response by removing markdown code blocks.
    Supports json, yaml, and generic code blocks.
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
import ast


def try_parse_json(content: str) -> dict:
    """
    Try to parse JSON, attempting to fix common LLM errors like missing closing braces
    and unescaped control characters.
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
        
        # Try different combinations of closing characters
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
    
    # Last resort: try Python's ast.literal_eval (more forgiving than JSON)
    try:
        result = ast.literal_eval(content)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass
    
    # If all else fails, raise a descriptive error
    raise JSONDecodeError(
        f"Could not parse JSON even after attempting fixes. Original error: {original_error}",
        content[:200],  # Show first 200 chars
        0
    )


def _fix_json_escaping(content: str) -> str:
    """
    Attempt to fix common JSON escaping issues in LLM-generated content.
    Specifically handles unescaped newlines and quotes within string values.
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
        
        if char == '\\':
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
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            else:
                result.append(char)
        else:
            result.append(char)
        
        i += 1
    
    return ''.join(result)
