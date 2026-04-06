"""Tests for custom exception hierarchy."""


from src.shared.exceptions import (
    ConfigurationException,
    DSLGeneratorException,
    JSONParseException,
    LLMConnectionException,
    LLMException,
    LLMProviderException,
    LLMTimeoutException,
    TemplateException,
    TemplateNotFoundException,
    TemplateRenderException,
    ValidationException,
    ValidationTimeoutException,
)


class TestDSLGeneratorException:
    """Tests for the base DSLGeneratorException class."""

    def test_basic_exception(self):
        """Test creating a basic exception with just a message."""
        exc = DSLGeneratorException("Something went wrong")
        assert str(exc) == "Something went wrong"
        assert exc.message == "Something went wrong"
        assert exc.code is None
        assert exc.context == {}

    def test_exception_with_code(self):
        """Test exception with error code."""
        exc = DSLGeneratorException("Error occurred", code="DSL001")
        assert str(exc) == "[DSL001] Error occurred"
        assert exc.code == "DSL001"

    def test_exception_with_context(self):
        """Test exception with context dictionary."""
        context = {"file": "test.py", "line": 42}
        exc = DSLGeneratorException("Error", code="DSL002", context=context)
        assert exc.context == context
        assert exc.context["file"] == "test.py"
        assert exc.context["line"] == 42

    def test_exception_inheritance(self):
        """Test that custom exception inherits from Exception."""
        exc = DSLGeneratorException("Test")
        assert isinstance(exc, Exception)


class TestLLMExceptions:
    """Tests for LLM-related exceptions."""

    def test_llm_exception_hierarchy(self):
        """Test that LLM exceptions inherit correctly."""
        exc = LLMException("LLM error")
        assert isinstance(exc, DSLGeneratorException)
        assert isinstance(exc, Exception)

    def test_llm_provider_exception(self):
        """Test LLMProviderException."""
        exc = LLMProviderException(
            "Provider initialization failed",
            code="LLM001",
            context={"provider": "groq"}
        )
        assert "Provider initialization failed" in str(exc)
        assert exc.context["provider"] == "groq"

    def test_llm_timeout_exception(self):
        """Test LLMTimeoutException."""
        exc = LLMTimeoutException(
            "Request timed out after 120s",
            code="LLM002",
            context={"timeout": 120}
        )
        assert isinstance(exc, LLMException)
        assert exc.context["timeout"] == 120

    def test_llm_connection_exception(self):
        """Test LLMConnectionException."""
        exc = LLMConnectionException(
            "Connection refused",
            code="LLM003"
        )
        assert isinstance(exc, LLMException)


class TestValidationExceptions:
    """Tests for validation-related exceptions."""

    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException("Validation failed")
        assert isinstance(exc, DSLGeneratorException)

    def test_validation_timeout_exception(self):
        """Test ValidationTimeoutException."""
        exc = ValidationTimeoutException(
            "npm install timed out",
            code="VAL001",
            context={"command": "npm install", "timeout": 180}
        )
        assert isinstance(exc, ValidationException)
        assert exc.context["command"] == "npm install"


class TestTemplateExceptions:
    """Tests for template-related exceptions."""

    def test_template_exception(self):
        """Test TemplateException."""
        exc = TemplateException("Template error")
        assert isinstance(exc, DSLGeneratorException)

    def test_template_not_found_exception(self):
        """Test TemplateNotFoundException."""
        exc = TemplateNotFoundException(
            "Template not found: entity.ts.j2",
            code="TEMPLATE002",
            context={"template_name": "entity.ts.j2"}
        )
        assert isinstance(exc, TemplateException)
        assert "entity.ts.j2" in str(exc)

    def test_template_render_exception(self):
        """Test TemplateRenderException."""
        exc = TemplateRenderException(
            "Failed to render template",
            code="TEMPLATE004",
            context={"template_name": "test.j2", "error": "Missing variable"}
        )
        assert isinstance(exc, TemplateException)


class TestOtherExceptions:
    """Tests for other custom exceptions."""

    def test_configuration_exception(self):
        """Test ConfigurationException."""
        exc = ConfigurationException(
            "Missing API key",
            code="CONFIG001",
            context={"key": "GROQ_API_KEY"}
        )
        assert isinstance(exc, DSLGeneratorException)
        assert exc.context["key"] == "GROQ_API_KEY"

    def test_json_parse_exception(self):
        """Test JSONParseException."""
        exc = JSONParseException(
            "Failed to parse JSON",
            code="JSON001",
            context={"content": '{"invalid": }'}
        )
        assert isinstance(exc, DSLGeneratorException)
        assert exc.context["content"] == '{"invalid": }'
