"""Shared utilities for validation modules."""

from .error_types import (
    ErrorCodes,
    RuntimeValidationResult,
    SyntacticValidationResult,
    ValidationError,
    ValidationResult,
    create_error,
)
from .project_utils import (
    get_project_paths,
    validate_project_structure,
    validate_source_directory,
    validate_typescript_config,
)
from .subprocess_utils import (
    SubprocessResult,
    check_process_running,
    run_command,
    start_process,
    terminate_process,
)

__all__ = [
    # Error types
    "ErrorCodes",
    "ValidationError",
    "ValidationResult",
    "RuntimeValidationResult",
    "SyntacticValidationResult",
    "create_error",
    # Project utilities
    "validate_project_structure",
    "validate_source_directory",
    "validate_typescript_config",
    "get_project_paths",
    # Subprocess utilities
    "SubprocessResult",
    "run_command",
    "start_process",
    "terminate_process",
    "check_process_running",
]
