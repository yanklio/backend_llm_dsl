"""Tests for textual DSL generation attachments."""

from packages.llm_providers.evaluation.textual_dsl_attachments import textual_dsl_attachment


def test_textual_dsl_attachment_spec_contains_reference() -> None:
    """Spec attachment should contain grammar-like reference content."""
    result = textual_dsl_attachment("spec")
    assert "TEXTUAL DSL REFERENCE" in result
    assert "Allowed primitive field types" in result
    assert "Do not use TypeScript syntax" in result


def test_textual_dsl_attachment_fewshot_contains_examples() -> None:
    """Few-shot attachment should include spec plus canonical examples."""
    result = textual_dsl_attachment("fewshot")
    assert "TEXTUAL DSL REFERENCE" in result
    assert "TEXTUAL DSL EXAMPLES" in result
    assert "Blog with authors and posts" in result


def test_textual_dsl_attachment_unknown_level_is_empty() -> None:
    """Unknown levels should leave the baseline prompt unchanged."""
    assert textual_dsl_attachment("") == ""
    assert textual_dsl_attachment("unknown") == ""
