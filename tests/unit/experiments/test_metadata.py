"""Smoke tests for experiment metadata module."""

from apps.experiments.metadata import (
    PROMPT_VERSION,
    PROVIDER_MODELS,
    build_run_metadata,
    model_name_for_provider,
    prompt_hash_for,
    record_identity,
    resume_key,
    short_hash,
)
from packages.llm_providers.core import prompts


class TestMetadataConstants:
    """Verify metadata constants are well-formed."""

    def test_prompt_version_is_string(self):
        assert isinstance(PROMPT_VERSION, str)
        assert len(PROMPT_VERSION) > 0

    def test_provider_models_has_all_keys(self):
        for pid in ["gemini", "groq", "ollama", "openrouter"]:
            assert pid in PROVIDER_MODELS
            assert isinstance(PROVIDER_MODELS[pid], str)


class TestMetadataFunctions:
    """Verify metadata helper functions return expected types."""

    def test_short_hash(self):
        result = short_hash("hello")
        assert isinstance(result, str)
        assert len(result) == 10

    def test_short_hash_custom_length(self):
        result = short_hash("hello", length=6)
        assert len(result) == 6

    def test_model_name_for_provider_known(self):
        name = model_name_for_provider("gemini")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_model_name_for_provider_unknown(self):
        assert model_name_for_provider("nonexistent") == "unknown"

    def test_prompt_hash_for_dsl(self):
        result = prompt_hash_for("dsl")
        assert isinstance(result, str)

    def test_prompt_hash_changes_when_actual_prompt_changes(self, monkeypatch):
        before = prompt_hash_for("textual-gen-spec")
        monkeypatch.setattr(prompts, "TEXTUAL_DSL_SPEC_REFERENCE", "changed prompt text")
        after = prompt_hash_for("textual-gen-spec")
        assert after != before

    def test_build_run_metadata(self):
        meta = build_run_metadata("openrouter", ["dsl", "raw"])
        assert meta["provider"] == "openrouter"
        assert meta["approaches"] == ["dsl", "raw"]
        assert "run_id" in meta
        assert "prompt_hashes" in meta

    def test_build_run_metadata_records_selected_cases(self):
        meta = build_run_metadata("openrouter", ["dsl"], case_ids=["TEST_CASE_2"])
        assert meta["selected_test_cases"] == ["TEST_CASE_2"]

    def test_build_run_metadata_records_model_override(self):
        meta = build_run_metadata("openrouter", ["dsl"], model_name="custom/model")
        assert meta["model_name"] == "custom/model"

    def test_record_identity(self):
        identity = record_identity(
            provider="groq",
            approach="raw",
            test_case="TEST_CASE_1",
            tier="simple",
        )
        assert identity["provider"] == "groq"
        assert identity["approach"] == "raw"
        assert identity["test_case"] == "TEST_CASE_1"
        assert identity["tier"] == "simple"

    def test_resume_key(self):
        record = {
            "test_case": "TC1",
            "approach": "dsl",
            "provider": "gemini",
            "model_name": "gemma",
            "prompt_hash": "abc123",
        }
        key = resume_key(record)
        assert key == ("TC1", "dsl", "gemini", "gemma", "abc123")
