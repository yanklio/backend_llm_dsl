"""Module to generate NestJS code from a YAML blueprint."""

import argparse
from pathlib import Path
from typing import Any, Optional

import yaml
from jinja2 import Environment, FileSystemLoader

from src.shared.exceptions import ConfigurationException
from src.shared.logs.logger import logger

from .core.modules.module import generate_module
from .core.modules.relation import handle_relations
from .core.root import generate_root_module
from .utils.type import to_ts_type


def _read_blueprint(blueprint_file: str) -> dict[str, Any]:
    """Read and parse the blueprint YAML file.

    Args:
        blueprint_file: Path to the blueprint YAML file.

    Returns:
        Parsed blueprint data.

    Raises:
        ConfigurationException: If file cannot be read or parsed.
    """
    try:
        with open(blueprint_file) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigurationException(
            f"Blueprint file not found: {blueprint_file}",
            code="CONFIG001",
            context={"file": blueprint_file},
        ) from e
    except yaml.YAMLError as e:
        raise ConfigurationException(
            f"Invalid YAML in blueprint file: {e}",
            code="CONFIG002",
            context={"file": blueprint_file, "error": str(e)},
        ) from e
    except Exception as e:
        raise ConfigurationException(
            f"Failed to read blueprint file: {e}",
            code="CONFIG003",
            context={"file": blueprint_file, "error": str(e)},
        ) from e

    if not isinstance(data, dict):
        raise ConfigurationException(
            "Blueprint must be a YAML dictionary",
            code="CONFIG004",
            context={"file": blueprint_file, "type": type(data).__name__},
        )

    return data


def _setup_jinja_env() -> Environment:
    """Setup Jinja2 environment with custom filters.

    Returns:
        Configured Jinja2 Environment.
    """
    script_dir = Path(__file__).parent
    template_dir = script_dir / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    env.filters["to_ts_type"] = to_ts_type
    return env


def _ensure_output_dir(nest_project_path: Optional[str]) -> Path:
    """Ensure the output directory exists.

    Args:
        nest_project_path: Path to the project directory.

    Returns:
        Path to the output directory.
    """
    base_output_dir = Path(nest_project_path) if nest_project_path else Path("nest_project")
    if not base_output_dir.exists():
        base_output_dir.mkdir(parents=True, exist_ok=True)
    return base_output_dir


def _enrich_modules_with_relations(
    modules_data: list[dict[str, Any]], relations_map: dict[tuple, dict[str, Any]]
) -> None:
    """Enrich module data with relation information.

    Args:
        modules_data: List of module configurations.
        relations_map: Map of relations keyed by (module, related_model).
    """
    for module_data in modules_data:
        module_name = module_data["name"]
        if "entity" in module_data and "relations" in module_data["entity"]:
            for relation in module_data["entity"]["relations"]:
                related_model = relation["model"]
                relation_key = (module_name, related_model)
                if relation_key in relations_map:
                    if "inverseField" in relations_map[relation_key]:
                        relation["inverseField"] = relations_map[relation_key]["inverseField"]
                    if "joinTable" in relations_map[relation_key]:
                        relation["joinTable"] = relations_map[relation_key]["joinTable"]
                    if "joinColumn" in relations_map[relation_key]:
                        relation["joinColumn"] = relations_map[relation_key]["joinColumn"]

        related_entities = []
        for (src, _dest), rel_data in relations_map.items():
            if src == module_name:
                related_entities.append(rel_data["model"])
        module_data["relatedEntities"] = related_entities


def main(blueprint_file: str, nest_project_path: Optional[str] = None) -> None:
    """Generate NestJS project from blueprint.

    Args:
        blueprint_file (str): Path to the blueprint YAML file.
        nest_project_path (Optional[str]): Output directory for the project.
                                           Defaults to "nest_project".

    Raises:
        ConfigurationException: If blueprint file is missing or invalid
    """
    data = _read_blueprint(blueprint_file)
    env = _setup_jinja_env()
    base_output_dir = _ensure_output_dir(nest_project_path)

    root_config = data.get("root", {})
    modules_data = data.get("modules", [])

    if not modules_data:
        logger.warn("No modules defined in blueprint!")
        return

    relations_map = handle_relations(modules_data)
    _enrich_modules_with_relations(modules_data, relations_map)

    generate_root_module(root_config, modules_data, env, base_output_dir)

    src_dir = base_output_dir / "src"
    for module_data in modules_data:
        generate_module(module_data, env, src_dir)

    logger.success(f"✓ Generation Complete! ({len(modules_data)} modules)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Nest.JS code from an enhanced YAML blueprint with root + sub-modules."
    )
    parser.add_argument(
        "blueprint_file",
        type=str,
        nargs="?",
        default="blueprint.yaml",
        help="The path to the YAML blueprint file (default: blueprint.yaml)",
    )
    parser.add_argument(
        "--nest-project",
        "-p",
        type=str,
        help="Path to existing NestJS project directory (default: nest_project)",
    )

    args = parser.parse_args()

    main(args.blueprint_file, args.nest_project)
