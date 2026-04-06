"""Tests for configuration management."""

from pathlib import Path

import pytest

from src.shared.config import (
    AppConfig,
    LLMConfig,
    LogConfig,
    TemplateConfig,
    ValidationConfig,
    get_config,
    reset_config,
)
from src.shared.exceptions import ConfigurationException


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = LLMConfig()
        assert config.timeout == 120
        assert config.retry_attempts == 3
        assert config.temperature == 0.1
        assert config.fallback_enabled is True

    def test_custom_values(self):
        """Test setting custom values."""
        config = LLMConfig(
            timeout=60,
            retry_attempts=5,
            temperature=0.5,
            fallback_enabled=False
        )
        assert config.timeout == 60
        assert config.retry_attempts == 5
        assert config.temperature == 0.5
        assert config.fallback_enabled is False

    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("LLM_TIMEOUT", "90")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
        config = LLMConfig()
        assert config.timeout == 90
        assert config.temperature == 0.7

    def test_validation_constraints(self):
        """Test that Pydantic validation works."""
        # Valid values
        config = LLMConfig(timeout=30, temperature=0.0)
        assert config.timeout == 30

        # Temperature bounds
        config = LLMConfig(temperature=2.0)
        assert config.temperature == 2.0


class TestValidationConfig:
    """Tests for ValidationConfig."""

    def test_default_values(self):
        """Test default validation configuration."""
        config = ValidationConfig()
        assert config.npm_install_timeout == 180
        assert config.tsc_timeout == 120
        assert config.app_start_timeout == 60
        assert config.app_port == 3000
        assert config.port_wait_time == 5
        assert config.port_check_retries == 10

    def test_custom_port(self):
        """Test setting custom port."""
        config = ValidationConfig(app_port=4000)
        assert config.app_port == 4000

    def test_environment_variable_override(self, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv("VALIDATION_APP_PORT", "5000")
        monkeypatch.setenv("VALIDATION_NPM_INSTALL_TIMEOUT", "240")
        config = ValidationConfig()
        assert config.app_port == 5000
        assert config.npm_install_timeout == 240


class TestTemplateConfig:
    """Tests for TemplateConfig."""

    def test_default_values(self):
        """Test default template configuration."""
        config = TemplateConfig()
        assert config.autoescape is False
        assert config.trim_blocks is True
        assert config.lstrip_blocks is True

    def test_templates_dir_default(self):
        """Test that templates_dir has a default value."""
        config = TemplateConfig()
        assert isinstance(config.templates_dir, Path)

    def test_get_templates_path_missing_directory(self, temp_dir):
        """Test that get_templates_path raises exception for missing directory."""
        config = TemplateConfig(templates_dir=temp_dir / "nonexistent")
        with pytest.raises(ConfigurationException) as exc_info:
            config.get_templates_path()
        assert "not found" in str(exc_info.value)
        assert exc_info.value.code == "TEMPLATE001"

    def test_get_templates_path_existing_directory(self, temp_dir):
        """Test get_templates_path with existing directory."""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        config = TemplateConfig(templates_dir=templates_dir)
        path = config.get_templates_path()
        assert path.exists()
        assert path.is_dir()


class TestLogConfig:
    """Tests for LogConfig."""

    def test_default_values(self):
        """Test default log configuration."""
        config = LogConfig()
        assert config.level == "INFO"
        assert config.verbose is False
        assert config.format == "%(message)s"
        assert config.show_timestamps is False

    def test_custom_log_level(self):
        """Test setting custom log level."""
        config = LogConfig(level="DEBUG", verbose=True)
        assert config.level == "DEBUG"
        assert config.verbose is True


class TestAppConfig:
    """Tests for main AppConfig."""

    def test_default_initialization(self):
        """Test that AppConfig initializes with default sub-configs."""
        config = AppConfig()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.validation, ValidationConfig)
        assert isinstance(config.template, TemplateConfig)
        assert isinstance(config.log, LogConfig)
        assert config.debug is False

    def test_nested_config_access(self):
        """Test accessing nested configuration values."""
        config = AppConfig()
        assert config.llm.timeout == 120
        assert config.validation.app_port == 3000
        assert config.log.level == "INFO"

    def test_custom_sub_configs(self):
        """Test providing custom sub-configurations."""
        custom_llm = LLMConfig(timeout=90)
        custom_validation = ValidationConfig(app_port=4000)

        config = AppConfig(llm=custom_llm, validation=custom_validation)
        assert config.llm.timeout == 90
        assert config.validation.app_port == 4000

    def test_debug_mode(self):
        """Test debug mode setting."""
        config = AppConfig(debug=True)
        assert config.debug is True


class TestGlobalConfig:
    """Tests for global configuration functions."""

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reset_config(self):
        """Test that reset_config creates a new instance."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2

    def test_config_values_persist(self):
        """Test that configuration values persist across get_config calls."""
        config1 = get_config()
        timeout1 = config1.llm.timeout
        config2 = get_config()
        timeout2 = config2.llm.timeout
        assert timeout1 == timeout2
