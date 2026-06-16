"""Tests for DSL code generation entry point."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.dsl.generate import (
    RELATION_COPY_FIELDS,
    _copy_relation_metadata,
    _enrich_modules_with_relations,
    _ensure_output_dir,
    _read_blueprint,
    _related_entities_for_module,
    _setup_jinja_env,
    main,
)
from src.shared.exceptions import ConfigurationException


class TestConstants:
    """Verify DSL generate module constants."""

    def test_relation_copy_fields(self):
        assert RELATION_COPY_FIELDS == ["inverseField", "joinTable", "joinColumn"]


class TestReadBlueprint:
    """Verify _read_blueprint function."""

    VALID_YAML = "root:\n  name: TestApp\nmodules: []\n"

    def test_valid_yaml_file(self, temp_dir):
        blueprint_file = temp_dir / "blueprint.yaml"
        blueprint_file.write_text(self.VALID_YAML)
        result = _read_blueprint(str(blueprint_file))
        assert result == {"root": {"name": "TestApp"}, "modules": []}

    def test_dsl_file(self, temp_dir):
        blueprint_file = temp_dir / "blueprint.dsl"
        blueprint_file.write_text("some dsl content")
        with patch("src.dsl.generate.compile_file") as mock_compile:
            mock_compile.return_value = {"root": {"name": "FromDSL"}, "modules": []}
            result = _read_blueprint(str(blueprint_file))
        mock_compile.assert_called_once_with(str(blueprint_file))
        assert result == {"root": {"name": "FromDSL"}, "modules": []}

    def test_missing_file_raises_configuration_exception(self):
        with pytest.raises(ConfigurationException) as exc_info:
            _read_blueprint("/nonexistent/path.yaml")
        assert exc_info.value.code == "CONFIG001"
        assert "not found" in str(exc_info.value)

    def test_invalid_yaml_raises_configuration_exception(self, temp_dir):
        blueprint_file = temp_dir / "invalid.yaml"
        blueprint_file.write_text("{{ invalid: yaml: broken")
        with pytest.raises(ConfigurationException) as exc_info:
            _read_blueprint(str(blueprint_file))
        assert exc_info.value.code == "CONFIG002"
        assert "Invalid YAML" in str(exc_info.value)

    def test_non_dict_yaml_raises_configuration_exception(self, temp_dir):
        blueprint_file = temp_dir / "list.yaml"
        blueprint_file.write_text("- item1\n- item2")
        with pytest.raises(ConfigurationException) as exc_info:
            _read_blueprint(str(blueprint_file))
        assert exc_info.value.code == "CONFIG004"
        assert "Blueprint must be a YAML dictionary" in str(exc_info.value)


class TestSetupJinjaEnv:
    """Verify _setup_jinja_env function."""

    def test_returns_environment_with_to_ts_type_filter(self):
        env = _setup_jinja_env()
        assert hasattr(env, "filters")
        assert "to_ts_type" in env.filters
        assert callable(env.filters["to_ts_type"])


class TestEnsureOutputDir:
    """Verify _ensure_output_dir function."""

    def test_creates_directory(self, temp_dir):
        output_path = temp_dir / "new_project"
        result = _ensure_output_dir(str(output_path))
        assert result == output_path
        assert output_path.exists()

    def test_existing_directory(self, temp_dir):
        existing = temp_dir / "existing"
        existing.mkdir()
        result = _ensure_output_dir(str(existing))
        assert result == existing
        assert existing.exists()

    def test_default_path(self, temp_dir):
        with patch("src.dsl.generate.Path") as MockPath:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            MockPath.return_value = mock_path
            _ensure_output_dir(None)
            MockPath.assert_called_once_with("nest_project")
            mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestEnrichModulesWithRelations:
    """Verify _enrich_modules_with_relations function."""

    def test_copies_relation_metadata(self):
        modules = [
            {
                "name": "User",
                "entity": {
                    "relations": [
                        {"type": "OneToMany", "model": "Post", "field": "posts"},
                    ],
                },
            },
        ]
        relations_map = {
            ("User", "Post"): {
                "model": "Post",
                "type": "OneToMany",
                "inverseField": "user",
                "joinTable": True,
            },
        }
        _enrich_modules_with_relations(modules, relations_map)
        rel = modules[0]["entity"]["relations"][0]
        assert rel["inverseField"] == "user"
        assert rel["joinTable"] is True

    def test_adds_related_entities(self):
        modules = [
            {"name": "User", "entity": {}},
            {"name": "Post", "entity": {}},
        ]
        relations_map = {
            ("User", "Post"): {"model": "Post", "type": "OneToMany", "field": "posts"},
        }
        _enrich_modules_with_relations(modules, relations_map)
        assert modules[0]["relatedEntities"] == ["Post"]
        assert modules[1]["relatedEntities"] == []

    def test_no_entity_key_skips_relations(self):
        modules = [
            {"name": "User"},
        ]
        _enrich_modules_with_relations(modules, {})
        assert modules[0].get("relatedEntities") == []


class TestCopyRelationMetadata:
    """Verify _copy_relation_metadata function."""

    def test_copies_inverse_field(self):
        relation = {"type": "OneToMany", "model": "Post"}
        relation_data = {"inverseField": "user"}
        _copy_relation_metadata(relation, relation_data)
        assert relation["inverseField"] == "user"

    def test_copies_join_table(self):
        relation = {"type": "ManyToMany", "model": "Role"}
        relation_data = {"joinTable": True}
        _copy_relation_metadata(relation, relation_data)
        assert relation["joinTable"] is True

    def test_copies_join_column(self):
        relation = {"type": "OneToOne", "model": "Profile"}
        relation_data = {"joinColumn": True}
        _copy_relation_metadata(relation, relation_data)
        assert relation["joinColumn"] is True

    def test_ignores_missing_keys(self):
        relation = {"type": "OneToMany", "model": "Post"}
        relation_data = {"unrelated_key": "value"}
        _copy_relation_metadata(relation, relation_data)
        assert "inverseField" not in relation
        assert "joinTable" not in relation
        assert "joinColumn" not in relation

    def test_copies_multiple_fields(self):
        relation = {"type": "ManyToMany", "model": "Role"}
        relation_data = {"inverseField": "users", "joinTable": True}
        _copy_relation_metadata(relation, relation_data)
        assert relation["inverseField"] == "users"
        assert relation["joinTable"] is True
        assert "joinColumn" not in relation


class TestRelatedEntitiesForModule:
    """Verify _related_entities_for_module function."""

    def test_returns_related_entity_names(self):
        relations_map = {
            ("User", "Post"): {"model": "Post", "type": "OneToMany", "field": "posts"},
            ("User", "Profile"): {"model": "Profile", "type": "OneToOne", "field": "profile"},
        }
        result = _related_entities_for_module("User", relations_map)
        assert set(result) == {"Post", "Profile"}

    def test_empty_when_no_relations(self):
        result = _related_entities_for_module("User", {})
        assert result == []

    def test_only_matches_source_module(self):
        relations_map = {
            ("User", "Post"): {"model": "Post", "type": "OneToMany", "field": "posts"},
            ("Post", "User"): {"model": "User", "type": "ManyToOne", "field": "user"},
        }
        result = _related_entities_for_module("Post", relations_map)
        assert result == ["User"]


class TestMain:
    """Verify main entry point orchestrates generation."""

    def test_generates_output(self, temp_dir):
        blueprint = str(temp_dir / "blueprint.yaml")
        output_dir = str(temp_dir / "output")
        modules = [
            {"name": "User", "entity": {"fields": []}},
            {"name": "Post", "entity": {"fields": []}},
        ]
        with (
            patch("src.dsl.generate._read_blueprint") as mock_read,
            patch("src.dsl.generate._setup_jinja_env") as mock_env_setup,
            patch("src.dsl.generate._ensure_output_dir") as mock_ensure_dir,
            patch("src.dsl.generate.handle_relations") as mock_relations,
            patch("src.dsl.generate._enrich_modules_with_relations") as mock_enrich,
            patch("src.dsl.generate.generate_root_module") as mock_root,
            patch("src.dsl.generate.generate_module") as mock_mod,
            patch("src.dsl.generate.logger"),
        ):
            mock_read.return_value = {"root": {"name": "Test"}, "modules": modules}
            mock_env_setup.return_value = MagicMock()
            mock_ensure_dir.return_value = Path(output_dir)
            mock_relations.return_value = {("User", "Post"): {}}

            main(blueprint, output_dir)

        mock_read.assert_called_once_with(blueprint)
        mock_ensure_dir.assert_called_once_with(output_dir)
        mock_relations.assert_called_once_with(modules)
        mock_enrich.assert_called_once_with(modules, mock_relations.return_value)
        mock_root.assert_called_once()
        assert mock_mod.call_count == 2

    def test_empty_modules_logs_warning(self, temp_dir):
        blueprint = str(temp_dir / "blueprint.yaml")
        with (
            patch("src.dsl.generate._read_blueprint") as mock_read,
            patch("src.dsl.generate._setup_jinja_env"),
            patch("src.dsl.generate._ensure_output_dir"),
            patch("src.dsl.generate.logger") as mock_logger,
        ):
            mock_read.return_value = {"root": {}, "modules": []}
            main(blueprint)

        mock_logger.warn.assert_called_once_with("No modules defined in blueprint!")
