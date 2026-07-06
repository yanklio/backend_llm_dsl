"""Relation handling logic for the DSL engine."""

from typing import Any

from packages.shared.logger import logger

RELATION_FLAG_RULES = {
    "ManyToMany": "joinTable",
    "OneToOne": "joinColumn",
}
RELATION_DEFAULTS = {"onDelete": "CASCADE"}


def handle_relations(modules_data: list[dict[str, Any]]) -> dict[tuple, dict[str, Any]]:
    """Process and validate entity relations.

    Args:
        modules_data (list[dict[str, Any]]): List of module configurations.

    Returns:
        dict[tuple, dict[str, Any]]: A map of valid relations keyed by (module, related_model).
    """
    relations_map = {}
    for module_data in modules_data:
        module_name = module_data["name"]
        for relation in module_data.get("entity", {}).get("relations", []):
            try:
                related_model = relation["model"]
                relation_data = _build_relation_data(module_name, related_model, relation)
                relations_map[(module_name, related_model)] = relation_data
            except KeyError:
                logger.error(f"Invalid relation format: {relation}")

    valid_relations = _filter_valid_relations(relations_map, modules_data)
    _apply_inverse_fields(valid_relations)
    _apply_ownership_flags(valid_relations)
    return valid_relations


def _build_relation_data(
    module_name: str,
    related_model: str,
    relation: dict[str, Any],
    module_positions: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build the normalized relation payload for one relation entry."""
    del module_name, module_positions
    relation_data = {
        "model": related_model,
        "type": relation["type"],
        "field": relation["field"],
        "onDelete": relation.get("onDelete", RELATION_DEFAULTS["onDelete"]),
    }
    return relation_data


def _filter_valid_relations(
    relations_map: dict[tuple, dict[str, Any]],
    modules_data: list[dict[str, Any]],
) -> dict[tuple, dict[str, Any]]:
    """Drop relations that point to missing modules."""
    module_names = {module_data["name"] for module_data in modules_data}
    valid_relations = {}

    for (module_name, related_model), relation_data in relations_map.items():
        if related_model in module_names:
            valid_relations[(module_name, related_model)] = relation_data
            continue

        logger.warn(f"Removing invalid relation: {module_name} -> {related_model} (module '{related_model}' not found)")

    return valid_relations


def _apply_inverse_fields(valid_relations: dict[tuple, dict[str, Any]]) -> None:
    """Populate inverse field names for bidirectional relations."""
    for (module_name, related_model), relation_data in valid_relations.items():
        reverse_key = (related_model, module_name)
        reverse_relation = valid_relations.get(reverse_key)
        if reverse_relation is not None:
            relation_data["inverseField"] = reverse_relation["field"]


def _apply_ownership_flags(valid_relations: dict[tuple, dict[str, Any]]) -> None:
    """Assign relation ownership decorators independent of module order."""
    for relation_data in valid_relations.values():
        relation_data.pop("joinTable", None)
        relation_data.pop("joinColumn", None)

    for key, relation_data in valid_relations.items():
        ownership_field = RELATION_FLAG_RULES.get(relation_data["type"])
        if ownership_field is None:
            continue

        module_name, related_model = key
        reverse_key = (related_model, module_name)
        reverse_relation = valid_relations.get(reverse_key)
        if reverse_relation is None:
            relation_data[ownership_field] = True
            continue

        if reverse_relation["type"] != relation_data["type"]:
            continue
        owner_key = min(key, reverse_key)
        if key == owner_key:
            relation_data[ownership_field] = True
