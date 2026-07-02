"""Tests for the public architecture package facades."""


def test_dsl_core_facade_exports_compiler_frontend() -> None:
    """DSL core facade should expose compiler frontend helpers."""
    import packages.dsl_core as dsl_core

    assert callable(dsl_core.tokenize)
    assert callable(dsl_core.parse)
    assert callable(dsl_core.resolve)
    assert callable(dsl_core.compile_textual_dsl)


def test_blueprint_facade_exports_loader() -> None:
    """Blueprint facade should expose canonical blueprint helpers."""
    import packages.blueprint as blueprint

    assert callable(blueprint.load_blueprint)
    assert callable(blueprint.validate_blueprint_structure)


def test_generator_facade_exports_nestjs_generator() -> None:
    """NestJS generator facade should expose the backend generator."""
    import packages.generator_nestjs as generator_nestjs

    assert callable(generator_nestjs.generate_nestjs)


def test_llm_provider_facade_is_separate_from_dsl_core() -> None:
    """LLM providers should remain outside the DSL core facade."""
    import packages.dsl_core as dsl_core
    import packages.llm_providers as llm_providers

    assert callable(llm_providers.LLMClient)
    assert not hasattr(dsl_core, "LLMClient")
