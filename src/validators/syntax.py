"""TypeScript validator module."""

from pathlib import Path
from typing import Optional

from src.validators.command import run_command
from src.validators.error_types import ErrorCodes, ValidationError, create_error


def _format_syntactic_error(error: ValidationError) -> dict[str, object]:
    """Convert a ValidationError into the public syntax result format."""
    return {
        "file": error.get("file", "unknown"),
        "line": error.get("line", 0),
        "column": error.get("column", 0),
        "message": error.get("message", ""),
        "code": error.get("code", ""),
    }


def _fallback_typescript_error(stderr: str) -> ValidationError:
    """Build a generic compile error when TypeScript output is unparseable."""
    stderr_lower = stderr.lower()

    if "timeout" in stderr_lower:
        return create_error("compile", "TypeScript compilation timeout", ErrorCodes.TIMEOUT)
    if "not found" in stderr_lower or "command not found" in stderr_lower:
        return create_error(
            "compile",
            "TypeScript compiler not found (npx tsc)",
            ErrorCodes.TSC_NOT_FOUND,
        )
    return create_error("compile", f"TypeScript compilation error: {stderr[:200]}", ErrorCodes.ERROR)


def validate_syntactic(project_path: Path) -> dict[str, object]:
    """Validate TypeScript syntax for the generated project.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, object]: Structured syntax validation result.
    """
    errors = check_typescript(project_path)

    return {
        "valid": len(errors) == 0,
        "total_files": 1,
        "error_count": len(errors),
        "errors": [_format_syntactic_error(error) for error in errors],
    }


def check_typescript(project_path: Path) -> list[ValidationError]:
    """Execute TypeScript compiler and return structured errors.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        list[ValidationError]: List of validation errors.
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
        errors.append(_fallback_typescript_error(result.stderr))

    return errors


def _parse_file_location(file_loc_part: str) -> Optional[tuple[str, str]]:
    """Parse file path and line/column coordinates from error line.

    Args:
        file_loc_part (str): Part of error line before "): error".

    Returns:
        Optional[tuple[str, str]]: Tuple of (file_path, line_col_string) or None if invalid format.
    """
    file_loc = file_loc_part.split("(")
    if len(file_loc) != 2:
        return None

    file_path = file_loc[0].strip()
    line_col = file_loc[1].strip()
    return file_path, line_col


def _parse_line_column(line_col: str) -> tuple[int, int]:
    """Parse line and column numbers from coordinate string.

    Args:
        line_col (str): String like "12,5".

    Returns:
        tuple[int, int]: Tuple of (line_num, col_num), defaults to (0, 0) if parsing fails.
    """
    line_num, col_num = 0, 0
    if "," in line_col:
        coords = line_col.split(",")
        try:
            line_num = int(coords[0])
            col_num = int(coords[1])
        except ValueError:
            pass
    return line_num, col_num


def _parse_error_code_and_message(error_part: str) -> tuple[str, str]:
    """Extract error code and message from error part.

    Args:
        error_part (str): Part after "): error " like "TS2322: Type 'string'..."

    Returns:
        tuple[str, str]: Tuple of (code, message).
    """
    code = ""
    message = error_part

    if error_part.startswith("TS"):
        code_end = error_part.find(":")
        if code_end > 0:
            code = error_part[:code_end].strip()
            message = error_part[code_end + 1 :].strip()

    return code, message


def _parse_typescript_error(line: str) -> Optional[ValidationError]:
    """Parse TypeScript compiler error line.

    Format: src/user/user.entity.ts(12,5): error TS2322: Type 'string' is not assignable to type 'number'.

    Args:
        line (str): Single line of TypeScript compiler output.

    Returns:
        Optional[ValidationError]: ValidationError dictionary or None if not an error line.
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
