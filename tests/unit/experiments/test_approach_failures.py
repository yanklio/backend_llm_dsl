"""Tests for experiment approach failure normalization."""

from pathlib import Path

from apps.experiments import approaches
from packages.llm_providers.providers.base import GenerationResult


def test_textual_gen_malformed_dsl_returns_failed_record(monkeypatch, temp_dir) -> None:
    """Malformed textual DSL should be a failed generation, not an escaped exception."""
    result = GenerationResult(
        content="entity Broken {",
        provider="openrouter",
        duration_seconds=1.2,
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        model_name="test-model",
        raw_content="```dsl\nentity Broken {\n```",
    )

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def generate(self, messages):
            return result

    monkeypatch.setattr(approaches, "LLMClient", FakeClient)

    generation = approaches.run_textual_gen_spec_approach(
        "TEST_CASE_X",
        {"requirement": "bad dsl"},
        Path(temp_dir),
        provider="openrouter",
    )

    assert generation["success"] is False
    assert generation["stage"] in {"parser", "lexer"}
    assert generation["metrics"]["total_tokens"] == 30
    assert generation["metrics"]["raw_response"] == "```dsl\nentity Broken {\n```"
