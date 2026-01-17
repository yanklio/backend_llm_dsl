from pathlib import Path
from typing import List

from ..shared.command import run_command
from ..shared.error_types import ErrorCodes, ValidationError, create_error


def check_typescript(project_path: Path) -> List[ValidationError]:
    """
    Execute TypeScript compiler and return structured errors.

    Args:
        project_path: Path to the NestJS project

    Returns:
        List of validation errors
    """
    result = run_command(["npx", "tsc", "--noEmit"], cwd=project_path, timeout=60)

    if result.success and not result.stdout and not result.stderr:
        return []

    errors = []
    output = result.stdout + result.stderr

    for line in output.splitlines():
        error = _parse_typescript_error(line)
        if error:
            errors.append(error)

    if not errors and not result.success:
        stderr_lower = result.stderr.lower()

        if "timeout" in stderr_lower:
            error_msg = "TypeScript compilation timeout"
            error_code = ErrorCodes.TIMEOUT
        elif "not found" in stderr_lower or "command not found" in stderr_lower:
            error_msg = "TypeScript compiler not found (npx tsc)"
            error_code = ErrorCodes.TSC_NOT_FOUND
        else:
            error_msg = f"TypeScript compilation error: {result.stderr[:200]}"
            error_code = ErrorCodes.ERROR

        errors.append(create_error("compile", error_msg, error_code))

    return errors


def _parse_file_location(file_loc_part: str) -> tuple[str, str] | None:
    """
    Parse file path and line/column coordinates from error line.

    Args:
        file_loc_part: Part of error line before "): error"

    Returns:
        Tuple of (file_path, line_col_string) or None if invalid format
    """
    file_loc = file_loc_part.split("(")
    if len(file_loc) != 2:
        return None

    file_path = file_loc[0].strip()
    line_col = file_loc[1].strip()
    return file_path, line_col


def _parse_line_column(line_col: str) -> tuple[int, int]:
    """
    Parse line and column numbers from coordinate string.

    Args:
        line_col: String like "12,5"

    Returns:
        Tuple of (line_num, col_num), defaults to (0, 0) if parsing fails
    """
    line_num, col_num = 0, 0
    if "," in line_col:
        coords = line_col.split(",")
        line_num = int(coords[0])
        col_num = int(coords[1])
    return line_num, col_num


def _parse_error_code_and_message(error_part: str) -> tuple[str, str]:
    """
    Extract error code and message from error part.

    Args:
        error_part: Part after "): error " like "TS2322: Type 'string'..."

    Returns:
        Tuple of (code, message)
    """
    code = ""
    message = error_part

    if error_part.startswith("TS"):
        code_end = error_part.find(":")
        if code_end > 0:
            code = error_part[:code_end].strip()
            message = error_part[code_end + 1 :].strip()

    return code, message


def _parse_typescript_error(line: str) -> ValidationError | None:
    """
    Parse TypeScript compiler error line.

    Format: src/user/user.entity.ts(12,5): error TS2322: Type 'string' is not assignable to type 'number'.

    Args:
        line: Single line of TypeScript compiler output

    Returns:
        ValidationError dictionary or None if not an error line
    """
    if "error TS" not in line:
        return None

    try:
        parts = line.split("): error ")
        if len(parts) != 2:
            return None

        file_loc_result = _parse_file_location(parts[0])
        if file_loc_result is None:
            return None

        file_path, line_col = file_loc_result
        line_num, col_num = _parse_line_column(line_col)
        code, message = _parse_error_code_and_message(parts[1])

        return create_error("compile", message, code, file=file_path, line=line_num, column=col_num)

    except Exception:
        return create_error("compile", line, ErrorCodes.PARSE_ERROR)
