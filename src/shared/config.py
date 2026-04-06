"""Configuration management for the DSL Generator project.

Provides centralized, type-safe configuration using Pydantic with support
for environment variables. Eliminates hardcoded values throughout the codebase.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Configuration for LLM providers and API calls.

    Attributes:
        timeout: Default timeout in seconds for LLM API calls
        retry_attempts: Number of retry attempts for failed API calls
        temperature: Temperature for LLM generation (0.0-1.0)
        fallback_enabled: Whether to enable fallback to next provider on failure
    """

    timeout: int = Field(default=120, ge=10, le=600)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    fallback_enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class ValidationConfig(BaseSettings):
    """Configuration for code validation (npm, tsc, runtime).

    Attributes:
        npm_install_timeout: Timeout for npm install in seconds
        tsc_timeout: Timeout for TypeScript compilation in seconds
        app_start_timeout: Timeout for app startup in seconds
        app_port: Port number for running the NestJS app
        port_wait_time: Time to wait for port to become available in seconds
        port_check_retries: Number of retries when checking if port is free
    """

    npm_install_timeout: int = Field(default=180, ge=30, le=600)
    tsc_timeout: int = Field(default=120, ge=30, le=300)
    app_start_timeout: int = Field(default=60, ge=10, le=180)
    app_port: int = Field(default=3000, ge=1024, le=65535)
    port_wait_time: int = Field(default=5, ge=1, le=30)
    port_check_retries: int = Field(default=10, ge=1, le=50)

    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class TemplateConfig(BaseSettings):
    """Configuration for Jinja2 template rendering.

    Attributes:
        templates_dir: Directory containing Jinja2 templates
        autoescape: Whether to enable autoescaping in templates
        trim_blocks: Whether to trim blocks in templates
        lstrip_blocks: Whether to lstrip blocks in templates
    """

    templates_dir: Path = Field(default=Path(__file__).parent.parent.parent / "templates")
    autoescape: bool = Field(default=False)
    trim_blocks: bool = Field(default=True)
    lstrip_blocks: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_prefix="TEMPLATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_templates_path(self) -> Path:
        """Get the absolute path to templates directory.

        Returns:
            Absolute path to templates directory

        Raises:
            ConfigurationException: If templates directory doesn't exist
        """
        from src.shared.exceptions import ConfigurationException

        templates_path = self.templates_dir.resolve()
        if not templates_path.exists():
            raise ConfigurationException(
                f"Templates directory not found: {templates_path}",
                code="TEMPLATE001",
                context={"path": str(templates_path)}
            )
        return templates_path


class LogConfig(BaseSettings):
    """Configuration for logging.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        verbose: Whether to enable verbose output
        format: Log message format
        show_timestamps: Whether to show timestamps in logs
    """

    level: str = Field(default="INFO")
    verbose: bool = Field(default=False)
    format: str = Field(default="%(message)s")
    show_timestamps: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class AppConfig(BaseSettings):
    """Main application configuration.

    Aggregates all configuration sections and provides a single entry point.

    Attributes:
        llm: LLM configuration
        validation: Validation configuration
        template: Template configuration
        log: Logging configuration
        debug: Whether debug mode is enabled
    """

    llm: LLMConfig = Field(default_factory=LLMConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    template: TemplateConfig = Field(default_factory=TemplateConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    debug: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **data):
        """Initialize app config.

        Loads configuration from environment variables and .env file.
        """
        super().__init__(**data)
        # Initialize sub-configs if not provided
        if not isinstance(self.llm, LLMConfig):
            self.llm = LLMConfig()
        if not isinstance(self.validation, ValidationConfig):
            self.validation = ValidationConfig()
        if not isinstance(self.template, TemplateConfig):
            self.template = TemplateConfig()
        if not isinstance(self.log, LogConfig):
            self.log = LogConfig()


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance.

    Returns:
        The global AppConfig instance

    Example:
        >>> config = get_config()
        >>> timeout = config.llm.timeout
        >>> port = config.validation.app_port
    """
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reset_config() -> None:
    """Reset the global configuration instance.

    Useful for testing or when configuration needs to be reloaded.
    """
    global _config
    _config = None
