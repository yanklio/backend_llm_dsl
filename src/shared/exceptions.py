"""Custom exception hierarchy for the DSL Generator project.

This module defines domain-specific exceptions to replace bare Exception catching
and provide better error handling throughout the application.
"""

from typing import Any, Optional


class DSLGeneratorException(Exception):
    """Base exception for all DSL Generator errors.

    Provides structured error information with error codes and context.

    Attributes:
        message: Human-readable error message
        code: Optional error code for programmatic handling
        context: Optional dictionary with additional error context
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            code: Optional error code (e.g., "DSL001")
            context: Optional context dict with additional information
        """
        self.message = message
        self.code = code
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Format exception as string."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


# === LLM-related exceptions ===

class LLMException(DSLGeneratorException):
    """Base exception for LLM-related errors."""
    pass


class LLMProviderException(LLMException):
    """Exception for provider initialization or API errors.

    Raised when:
    - Provider fails to initialize (missing API keys, invalid config)
    - Provider API returns an error
    - Provider-specific errors occur
    """
    pass


class LLMTimeoutException(LLMException):
    """Exception for LLM request timeouts.

    Raised when an LLM API call exceeds the configured timeout period.
    """
    pass


class LLMConnectionException(LLMException):
    """Exception for LLM connection failures.

    Raised when:
    - Network connection to LLM provider fails
    - DNS resolution fails
    - Connection is refused
    """
    pass


# === Validation exceptions ===

class ValidationException(DSLGeneratorException):
    """Base exception for validation errors."""
    pass


class ValidationTimeoutException(ValidationException):
    """Exception for validation timeouts.

    Raised when validation operations (npm install, tsc, etc.) exceed timeout.
    """
    pass


# === Template exceptions ===

class TemplateException(DSLGeneratorException):
    """Base exception for template rendering errors."""
    pass


class TemplateNotFoundException(TemplateException):
    """Exception for missing template files.

    Raised when a requested Jinja2 template file cannot be found.
    """
    pass


class TemplateRenderException(TemplateException):
    """Exception for template rendering failures.

    Raised when:
    - Template syntax is invalid
    - Template variables are missing or invalid
    - Template rendering fails for any reason
    """
    pass


# === Configuration exceptions ===

class ConfigurationException(DSLGeneratorException):
    """Exception for configuration errors.

    Raised when:
    - Configuration files are missing or invalid
    - Environment variables are missing
    - Configuration validation fails
    """
    pass


# === JSON parsing exceptions ===

class JSONParseException(DSLGeneratorException):
    """Exception for JSON parsing failures.

    Raised when JSON content cannot be parsed even after attempting repairs.
    """
    pass
