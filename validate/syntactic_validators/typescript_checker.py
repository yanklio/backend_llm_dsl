"""TypeScript compilation checking utilities."""

from pathlib import Path
from typing import List

from ..shared.error_types import ErrorCodes, ValidationError, create_error
from ..shared.subprocess_utils import run_command


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

    # Handle special cases
    if not errors and not result.success:
        if "timeout" in result.stderr.lower():
            errors.append(
                create_error("compile", "TypeScript compilation timeout", ErrorCodes.TIMEOUT)
            )
        elif "not found" in result.stderr.lower() or "command not found" in result.stderr.lower():
            errors.append(
                create_error(
                    "compile",
                    "TypeScript compiler not found (npx tsc)",
                    ErrorCodes.TSC_NOT_FOUND,
                )
            )
        else:
            errors.append(
                create_error(
                    "compile",
                    f"TypeScript compilation error: {result.stderr[:200]}",
                    ErrorCodes.ERROR,
                )
            )

    return errors


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

        file_loc = parts[0].split("(")
        if len(file_loc) != 2:
            return None

        file_path = file_loc[0].strip()
        line_col = file_loc[1].strip()

        line_num, col_num = 0, 0
        if "," in line_col:
            coords = line_col.split(",")
            line_num = int(coords[0])
            col_num = int(coords[1])

        error_part = parts[1]
        code = ""
        message = error_part

        if error_part.startswith("TS"):
            code_end = error_part.find(":")
            if code_end > 0:
                code = error_part[:code_end].strip()
                message = error_part[code_end + 1 :].strip()

        return create_error("compile", message, code, file=file_path, line=line_num, column=col_num)

    except Exception:
        return create_error("compile", line, ErrorCodes.PARSE_ERROR)
