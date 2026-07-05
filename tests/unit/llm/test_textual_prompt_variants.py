"""Tests for frozen textual generation prompt variants."""

from apps.experiments.metadata import prompt_hash_for
from packages.llm_providers.core.prompts import (
    RAW_CODE_SYSTEM_PROMPT,
    TextualPromptVariant,
    build_textual_generation_messages,
)


def _prompt_text(variant: TextualPromptVariant) -> str:
    return "\n".join(str(message.content) for message in build_textual_generation_messages("Build an app", variant))


def test_baseline_prompt_has_no_formal_spec_or_examples() -> None:
    """Baseline prompt remains intentionally minimal."""
    text = _prompt_text(TextualPromptVariant.BASELINE)
    assert "Supported declarations" not in text
    assert "Example 1" not in text
    assert "Do not use TypeScript" in text
    assert "TypeOrmModule" in text
    assert "Never use semicolons" in text


def test_spec_prompt_has_reference_without_examples() -> None:
    """Spec prompt includes the compact DSL reference only."""
    text = _prompt_text(TextualPromptVariant.SPEC)
    assert "Supported declarations" in text
    assert "Example 1" not in text


def test_fewshot_prompt_has_reference_and_three_examples() -> None:
    """Few-shot prompt includes exactly three canonical examples."""
    text = _prompt_text(TextualPromptVariant.FEWSHOT)
    assert "Supported declarations" in text
    assert text.count("Example ") == 3


def test_textual_prompt_hashes_are_distinct() -> None:
    """Final textual variants have stable distinct prompt identities."""
    hashes = {
        prompt_hash_for("textual-gen-baseline"),
        prompt_hash_for("textual-gen-spec"),
        prompt_hash_for("textual-gen-fewshot"),
    }
    assert len(hashes) == 3


def test_raw_prompt_requires_null_safe_find_one() -> None:
    """Raw file-map prompt prevents TypeORM nullable lookup build failures."""
    assert "findOne/findOneBy can return null" in RAW_CODE_SYSTEM_PROMPT
    assert "NotFoundException" in RAW_CODE_SYSTEM_PROMPT
    assert "COMPILE-SAFE SERVICE EXAMPLE" in RAW_CODE_SYSTEM_PROMPT
