"""Syntactic validation for NestJS projects."""

from pathlib import Path

from ..shared.error_types import SyntacticValidationResult
from ..shared.project_utils import (
    validate_source_directory,
    validate_typescript_config,
)
from .typescript_checker import check_typescript


def validate_project(project_path: str) -> SyntacticValidationResult:
    """
    Validate syntactic correctness of a NestJS project using tsc --noEmit.

    Args:
        project_path: Path to NestJS project directory

    Returns:
        SyntacticValidationResult with validation results containing:
        - valid: bool
        - total_files: int
        - error_count: int
        - errors: List[Dict] with file, line, column, message, code
    """
    project_path_obj = Path(project_path)
    errors = []

    # Validate source directory
    src_validation = validate_source_directory(project_path_obj)
    total_files = src_validation["ts_files_count"]

    if src_validation["error"]:
        errors.append(src_validation["error"])
        return SyntacticValidationResult(
            valid=False,
            total_files=total_files,
            error_count=len(errors),
            errors=errors,
        )

    # Validate TypeScript configuration
    config_error = validate_typescript_config(project_path_obj)
    if config_error:
        errors.append(config_error)
        return SyntacticValidationResult(
            valid=False,
            total_files=total_files,
            error_count=len(errors),
            errors=errors,
        )

    # Run TypeScript compiler
    compile_errors = check_typescript(project_path_obj)
    errors.extend(compile_errors)

    return SyntacticValidationResult(
        valid=len(errors) == 0,
        total_files=total_files,
        error_count=len(errors),
        errors=errors,
    )


__all__ = [
    "validate_project",
    "check_typescript",
]
