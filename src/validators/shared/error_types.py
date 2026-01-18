"""Shared error types and structures for validation."""

from typing import Dict, List, TypedDict


class ValidationError(TypedDict, total=False):
    """Standard validation error structure."""

    stage: str
    message: str
    code: str
    file: str
    line: int
    column: int
    endpoint: str


class ValidationResult(TypedDict, total=False):
    """Standard validation result structure."""

    valid: bool
    errors: List[ValidationError]


class RuntimeValidationResult(ValidationResult):
    """Runtime validation specific result."""

    build_success: bool
    start_success: bool
    endpoint_tests: Dict


class SyntacticValidationResult(ValidationResult):
    """Syntactic validation specific result."""

    total_files: int
    error_count: int


# Error codes
class ErrorCodes:
    """Standard error codes for validation."""

    # Setup errors
    MISSING_PACKAGE_JSON = "MISSING_PACKAGE_JSON"
    MISSING_SRC = "MISSING_SRC"
    MISSING_CONFIG = "MISSING_CONFIG"
    NO_FILES = "NO_FILES"

    # NPM errors
    NPM_NOT_FOUND = "NPM_NOT_FOUND"
    INSTALL_FAILED = "INSTALL_FAILED"
    INSTALL_TIMEOUT = "INSTALL_TIMEOUT"
    INSTALL_ERROR = "INSTALL_ERROR"
    BUILD_FAILED = "BUILD_FAILED"
    BUILD_TIMEOUT = "BUILD_TIMEOUT"
    BUILD_ERROR = "BUILD_ERROR"
    START_CRASHED = "START_CRASHED"
    START_ERROR = "START_ERROR"

    # TypeScript errors
    TSC_NOT_FOUND = "TSC_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    PARSE_ERROR = "PARSE_ERROR"

    # Endpoint testing errors
    APP_CRASHED = "APP_CRASHED"
    ENDPOINT_FAILED = "ENDPOINT_FAILED"
    ENDPOINT_TEST_ERROR = "ENDPOINT_TEST_ERROR"

    # Generic
    ERROR = "ERROR"


def create_error(stage: str, message: str, code: str, **kwargs) -> ValidationError:
    """
    Create a standardized validation error.

    Args:
        stage: The validation stage where error occurred
        message: Human-readable error message
        code: Error code from ErrorCodes
        **kwargs: Additional error fields (file, line, column, endpoint, etc.)

    Returns:
        ValidationError dictionary
    """
    error: ValidationError = {"stage": stage, "message": message, "code": code}
    error.update(kwargs)
    return error
