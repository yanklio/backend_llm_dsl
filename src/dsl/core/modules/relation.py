"""Relation handling logic for the DSL engine."""

import sys
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from src.shared.logs.logger import logger


def handle_relations(
    modules_data: List[Dict[str, Any]], env: Environment, base_output_dir: Path
) -> Dict[tuple, Dict[str, Any]]:
    """Process and validate entity relations.

    Args:
        modules_data (List[Dict[str, Any]]): List of module configurations.
        env (Environment): Jinja2 environment (unused here but matches signature).
        base_output_dir (Path): Base output directory (unused here).

    Returns:
        Dict[tuple, Dict[str, Any]]: A map of valid relations keyed by (module, related_model).
    """
    relations_map = {}
    for module_data in modules_data:
        module_name = module_data["name"]
        for relation in module_data.get("entity", {}).get("relations", []):
            try:
                related_model = relation["model"]
                relation_type = relation["type"]
                relation_field = relation["field"]
                relation_on_delete = relation.get("onDelete", "CASCADE")

                relations_map[(module_name, related_model)] = {
                    "model": related_model,
                    "type": relation_type,
                    "field": relation_field,
                    "onDelete": relation_on_delete,
                }

            except KeyError:
                logger.error(f"Invalid relation format: {relation}")

    module_names = {module_data["name"] for module_data in modules_data}
    valid_relations = {}
    for (module_name, related_model), relation_data in relations_map.items():
        if related_model in module_names:
            valid_relations[(module_name, related_model)] = relation_data
        else:
            logger.warn(
                f"Removing invalid relation: {module_name} -> {related_model} "
                f"(module '{related_model}' not found)"
            )

    for (module_name, related_model), relation_data in valid_relations.items():
        reverse_key = (related_model, module_name)
        if reverse_key in valid_relations:
            reverse_relation = valid_relations[reverse_key]
            relation_data["inverseField"] = reverse_relation["field"]

    return valid_relations
