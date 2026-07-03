"""Configuration management for the DSL Generator project.

Provides centralized, type-safe configuration using Pydantic with support
for environment variables. Eliminates hardcoded values throughout the codebase.
"""

import os
from pathlib import Path
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field


def _coerce_env_value(raw_value: str, annotation: object) -> object:
    """Coerce an environment string to the annotated field type."""
    if annotation is bool:
        return raw_value.lower() in {"1", "true", "yes", "on"}
    if annotation is int:
        return int(raw_value)
    if annotation is float:
        return float(raw_value)
    if annotation is Path:
        return Path(raw_value)
    return raw_value


class EnvSettings(BaseModel):
    """Minimal environment-backed settings base used by project config classes."""

    model_config = {"extra": "ignore"}

    @classmethod
    def env_prefix(cls) -> str:
        """Return the environment prefix for a settings class."""
        return str(cls.__dict__.get("_env_prefix", ""))

    def __init__(self, **data: Any) -> None:
        """Initialize settings with values from explicit data or environment."""
        values = dict(data)
        prefix = self.env_prefix()
        for name, field in self.__class__.model_fields.items():
            env_name = f"{prefix}{name}".upper()
            if name not in values and env_name in os.environ:
                values[name] = _coerce_env_value(os.environ[env_name], field.annotation)
        super().__init__(**values)


SUB_CONFIG_FIELDS = ["llm", "validation", "template", "log"]


class LLMConfig(EnvSettings):
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

    _env_prefix: ClassVar[str] = "LLM_"


class ValidationConfig(EnvSettings):
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

    _env_prefix: ClassVar[str] = "VALIDATION_"


class TemplateConfig(EnvSettings):
    """Configuration for Jinja2 template rendering.

    Attributes:
        templates_dir: Directory containing Jinja2 templates
        autoescape: Whether to enable autoescaping in templates
        trim_blocks: Whether to trim blocks in templates
        lstrip_blocks: Whether to lstrip blocks in templates
    """

    templates_dir: Path = Field(default=Path(__file__).parent.parent / "dsl" / "templates")
    autoescape: bool = Field(default=False)
    trim_blocks: bool = Field(default=True)
    lstrip_blocks: bool = Field(default=True)

    _env_prefix: ClassVar[str] = "TEMPLATE_"

    def get_templates_path(self) -> Path:
        """Get the absolute path to templates directory.

        Returns:
            Absolute path to templates directory

        Raises:
            ConfigurationException: If templates directory doesn't exist
        """
        from packages.shared.exceptions import ConfigurationException

        templates_path = self.templates_dir.resolve()
        if not templates_path.exists():
            raise ConfigurationException(
                f"Templates directory not found: {templates_path}",
                code="TEMPLATE001",
                context={"path": str(templates_path)},
            )
        return templates_path


class LogConfig(EnvSettings):
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

    _env_prefix: ClassVar[str] = "LOG_"


class AppConfig(EnvSettings):
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

    _env_prefix: ClassVar[str] = "APP_"

    def __init__(self, **data):
        """Initialize app config.

        Loads configuration from environment variables and .env file.
        """
        super().__init__(**data)
        self._ensure_sub_configs()

    def _ensure_sub_configs(self) -> None:
        """Recreate nested configs if Pydantic did not instantiate them."""
        config_types = {
            "llm": LLMConfig,
            "validation": ValidationConfig,
            "template": TemplateConfig,
            "log": LogConfig,
        }
        for field_name in SUB_CONFIG_FIELDS:
            config_type = config_types[field_name]
            if not isinstance(getattr(self, field_name), config_type):
                setattr(self, field_name, config_type())


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
