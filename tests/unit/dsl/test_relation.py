"""Tests for DSL engine relation processing."""

from src.dsl.core.modules.relation import (
    RELATION_DEFAULTS,
    RELATION_FLAG_RULES,
    _apply_inverse_fields,
    _build_relation_data,
    _filter_valid_relations,
    handle_relations,
)


class TestConstants:
    """Verify relation module constants."""

    def test_relation_flag_rules_has_expected_keys(self):
        assert "ManyToMany" in RELATION_FLAG_RULES
        assert "OneToOne" in RELATION_FLAG_RULES

    def test_relation_defaults_has_on_delete(self):
        assert RELATION_DEFAULTS["onDelete"] == "CASCADE"


class TestHandleRelations:
    """Verify handle_relations end-to-end processing."""

    def test_empty_modules_list(self):
        assert handle_relations([]) == {}

    def test_single_module_no_relations(self):
        modules = [{"name": "User", "entity": {"fields": []}}]
        assert handle_relations(modules) == {}

    def test_module_without_entity_key(self):
        modules = [{"name": "User"}]
        assert handle_relations(modules) == {}

    def test_one_to_many_relation_to_existing_module(self):
        modules = [
            {"name": "User", "entity": {"fields": [{"name": "id", "type": "number"}]}},
            {
                "name": "Post",
                "entity": {
                    "fields": [{"name": "title", "type": "string"}],
                    "relations": [{"type": "ManyToOne", "model": "User", "field": "user"}],
                },
            },
        ]
        result = handle_relations(modules)
        assert ("Post", "User") in result
        assert result[("Post", "User")]["model"] == "User"
        assert result[("Post", "User")]["type"] == "ManyToOne"
        assert result[("Post", "User")]["field"] == "user"

    def test_many_to_many_join_table_on_lower_index(self):
        modules = [
            {"name": "User", "entity": {"fields": []}},
            {"name": "Role", "entity": {"fields": []}},
        ]
        modules[0]["entity"]["relations"] = [{"type": "ManyToMany", "model": "Role", "field": "roles"}]
        result = handle_relations(modules)
        assert result[("User", "Role")].get("joinTable") is True

    def test_one_to_one_join_column_on_higher_index(self):
        modules = [
            {"name": "User", "entity": {"fields": []}},
            {"name": "Profile", "entity": {"fields": []}},
        ]
        modules[1]["entity"]["relations"] = [{"type": "OneToOne", "model": "User", "field": "user"}]
        result = handle_relations(modules)
        assert result[("Profile", "User")].get("joinColumn") is True

    def test_relation_to_nonexistent_module_filtered(self, capsys):
        modules = [
            {
                "name": "User",
                "entity": {"relations": [{"type": "OneToMany", "model": "NonExistent", "field": "nonexistents"}]},
            }
        ]
        result = handle_relations(modules)
        captured = capsys.readouterr()
        assert result == {}
        assert "NonExistent" in captured.out

    def test_bidirectional_inverse_field_populated(self):
        modules = [
            {"name": "User", "entity": {"fields": []}},
            {"name": "Post", "entity": {"fields": []}},
        ]
        modules[0]["entity"]["relations"] = [{"type": "OneToMany", "model": "Post", "field": "posts"}]
        modules[1]["entity"]["relations"] = [{"type": "ManyToOne", "model": "User", "field": "user"}]
        result = handle_relations(modules)
        assert result[("User", "Post")]["inverseField"] == "user"
        assert result[("Post", "User")]["inverseField"] == "posts"

    def test_custom_on_delete(self):
        modules = [
            {"name": "User", "entity": {"fields": []}},
            {"name": "Post", "entity": {"fields": []}},
        ]
        modules[1]["entity"]["relations"] = [
            {"type": "ManyToOne", "model": "User", "field": "user", "onDelete": "SET NULL"}
        ]
        result = handle_relations(modules)
        assert result[("Post", "User")]["onDelete"] == "SET NULL"

    def test_default_on_delete_when_not_specified(self):
        modules = [
            {"name": "User", "entity": {"fields": []}},
            {"name": "Post", "entity": {"fields": []}},
        ]
        modules[1]["entity"]["relations"] = [{"type": "ManyToOne", "model": "User", "field": "user"}]
        result = handle_relations(modules)
        assert result[("Post", "User")]["onDelete"] == "CASCADE"

    def test_missing_model_key_logs_error(self, capsys):
        modules = [
            {
                "name": "User",
                "entity": {"relations": [{"type": "OneToMany", "field": "items"}]},
            }
        ]
        result = handle_relations(modules)
        captured = capsys.readouterr()
        assert result == {}
        assert "Invalid relation format" in captured.out

    def test_relation_type_not_in_flag_rules(self):
        modules = [
            {"name": "A", "entity": {"fields": []}},
            {"name": "B", "entity": {"fields": []}},
        ]
        modules[0]["entity"]["relations"] = [{"type": "CustomRel", "model": "B", "field": "bs"}]
        result = handle_relations(modules)
        assert ("A", "B") in result
        assert "joinTable" not in result[("A", "B")]
        assert "joinColumn" not in result[("A", "B")]


class TestBuildRelationData:
    """Verify _build_relation_data payload construction."""

    def test_basic_relation(self):
        positions = {"User": 0, "Post": 1}
        relation = {"type": "ManyToOne", "model": "User", "field": "user"}
        result = _build_relation_data("Post", "User", relation, positions)
        assert result == {"model": "User", "type": "ManyToOne", "field": "user", "onDelete": "CASCADE"}

    def test_many_to_many_source_lower_than_related(self):
        positions = {"User": 0, "Role": 1}
        relation = {"type": "ManyToMany", "model": "Role", "field": "roles"}
        result = _build_relation_data("User", "Role", relation, positions)
        assert result.get("joinTable") is True

    def test_many_to_many_source_higher_than_related(self):
        positions = {"User": 0, "Role": 1}
        relation = {"type": "ManyToMany", "model": "User", "field": "users"}
        result = _build_relation_data("Role", "User", relation, positions)
        assert "joinTable" not in result

    def test_one_to_one_source_higher_than_related(self):
        positions = {"User": 0, "Profile": 1}
        relation = {"type": "OneToOne", "model": "User", "field": "user"}
        result = _build_relation_data("Profile", "User", relation, positions)
        assert result.get("joinColumn") is True

    def test_one_to_one_source_lower_than_related(self):
        positions = {"User": 0, "Profile": 1}
        relation = {"type": "OneToOne", "model": "Profile", "field": "profile"}
        result = _build_relation_data("User", "Profile", relation, positions)
        assert "joinColumn" not in result

    def test_unrecognized_relation_type(self):
        positions = {"A": 0, "B": 1}
        relation = {"type": "CustomRelation", "model": "B", "field": "bs"}
        result = _build_relation_data("A", "B", relation, positions)
        assert "joinTable" not in result
        assert "joinColumn" not in result
        assert result["type"] == "CustomRelation"

    def test_related_model_not_in_positions(self):
        positions = {"User": 0}
        relation = {"type": "ManyToMany", "model": "Ghost", "field": "ghosts"}
        result = _build_relation_data("User", "Ghost", relation, positions)
        assert "joinTable" not in result
        assert result["model"] == "Ghost"

    def test_custom_on_delete_preserved(self):
        positions = {"User": 0, "Post": 1}
        relation = {"type": "ManyToOne", "model": "User", "field": "user", "onDelete": "SET NULL"}
        result = _build_relation_data("Post", "User", relation, positions)
        assert result["onDelete"] == "SET NULL"


class TestFilterValidRelations:
    """Verify _filter_valid_relations filtering logic."""

    def test_all_valid_pass_through(self):
        relations = {("User", "Post"): {"model": "Post", "type": "OneToMany", "field": "posts"}}
        modules = [{"name": "User"}, {"name": "Post"}]
        assert _filter_valid_relations(relations, modules) == relations

    def test_invalid_relations_removed(self, capsys):
        relations = {
            ("User", "Post"): {"model": "Post", "type": "OneToMany", "field": "posts"},
            ("User", "Ghost"): {"model": "Ghost", "type": "OneToMany", "field": "ghosts"},
        }
        modules = [{"name": "User"}, {"name": "Post"}]
        result = _filter_valid_relations(relations, modules)
        captured = capsys.readouterr()
        assert ("User", "Post") in result
        assert ("User", "Ghost") not in result
        assert "Ghost" in captured.out

    def test_empty_map(self):
        assert _filter_valid_relations({}, [{"name": "User"}]) == {}


class TestApplyInverseFields:
    """Verify _apply_inverse_fields populates inverseField."""

    def test_bidirectional_pair(self):
        relations = {
            ("User", "Post"): {"model": "Post", "type": "OneToMany", "field": "posts"},
            ("Post", "User"): {"model": "User", "type": "ManyToOne", "field": "user"},
        }
        _apply_inverse_fields(relations)
        assert relations[("User", "Post")]["inverseField"] == "user"
        assert relations[("Post", "User")]["inverseField"] == "posts"

    def test_unidirectional_no_inverse_field(self):
        relations = {
            ("User", "Post"): {"model": "Post", "type": "OneToMany", "field": "posts"},
        }
        _apply_inverse_fields(relations)
        assert "inverseField" not in relations[("User", "Post")]

    def test_empty_map(self):
        _apply_inverse_fields({})
