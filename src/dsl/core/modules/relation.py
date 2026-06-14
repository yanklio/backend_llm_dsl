"""Relation handling logic for the DSL engine."""

from typing import Any

from src.shared.logger import logger

RELATION_FLAG_RULES = {
    "ManyToMany": lambda source_index, related_index: {"joinTable": source_index < related_index},
    "OneToOne": lambda source_index, related_index: {"joinColumn": source_index > related_index},
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
    module_order = [module_data["name"] for module_data in modules_data]
    module_positions = {module_name: index for index, module_name in enumerate(module_order)}

    for module_data in modules_data:
        module_name = module_data["name"]
        for relation in module_data.get("entity", {}).get("relations", []):
            try:
                related_model = relation["model"]
                relation_data = _build_relation_data(
                    module_name,
                    related_model,
                    relation,
                    module_positions,
                )
                relations_map[(module_name, related_model)] = relation_data
            except KeyError:
                logger.error(f"Invalid relation format: {relation}")

    valid_relations = _filter_valid_relations(relations_map, modules_data)
    _apply_inverse_fields(valid_relations)
    return valid_relations


def _build_relation_data(
    module_name: str,
    related_model: str,
    relation: dict[str, Any],
    module_positions: dict[str, int],
) -> dict[str, Any]:
    """Build the normalized relation payload for one relation entry."""
    relation_data = {
        "model": related_model,
        "type": relation["type"],
        "field": relation["field"],
        "onDelete": relation.get("onDelete", RELATION_DEFAULTS["onDelete"]),
    }

    rule = RELATION_FLAG_RULES.get(relation["type"])
    if rule is None or related_model not in module_positions:
        return relation_data

    source_index = module_positions[module_name]
    related_index = module_positions[related_model]
    for field_name, enabled in rule(source_index, related_index).items():
        if enabled:
            relation_data[field_name] = True
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
