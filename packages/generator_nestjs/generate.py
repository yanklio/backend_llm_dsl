"""Generate NestJS code from canonical blueprint dictionaries or files."""

import argparse
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from packages.blueprint import coerce_blueprint, load_blueprint
from packages.dsl_core.compiler import compile_file
from packages.shared.logger import logger

from .core.modules.module import generate_module
from .core.modules.relation import handle_relations
from .core.root import generate_root_module
from .utils.ts_types import to_ts_type

RELATION_COPY_FIELDS = ["inverseField", "joinTable", "joinColumn"]


def _read_blueprint(blueprint_file: str | Path) -> dict[str, Any]:
    """Backward-compatible helper to load a .dsl or YAML blueprint file."""
    source = Path(blueprint_file)
    if source.suffix == ".dsl":
        return compile_file(str(source))
    return load_blueprint(source)


def _setup_jinja_env() -> Environment:
    """Set up Jinja2 environment with custom filters."""
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    env.filters["to_ts_type"] = to_ts_type
    return env


def _ensure_output_dir(output_dir: str | Path | None = None) -> Path:
    """Ensure the output directory exists."""
    base_output_dir = Path(output_dir or "nest_project")
    base_output_dir.mkdir(parents=True, exist_ok=True)
    return base_output_dir


def _enrich_modules_with_relations(
    modules_data: list[dict[str, Any]], relations_map: dict[tuple, dict[str, Any]]
) -> None:
    """Enrich module data with inferred relation information."""
    for module_data in modules_data:
        module_name = module_data["name"]
        if "entity" in module_data and "relations" in module_data["entity"]:
            for relation in module_data["entity"]["relations"]:
                relation_data = relations_map.get((module_name, relation["model"]))
                if relation_data is not None:
                    _copy_relation_metadata(relation, relation_data)
        module_data["relatedEntities"] = _related_entities_for_module(module_name, relations_map)


def _copy_relation_metadata(relation: dict[str, Any], relation_data: dict[str, Any]) -> None:
    """Copy derived relation metadata into the original module blueprint."""
    for field_name in RELATION_COPY_FIELDS:
        if field_name in relation_data:
            relation[field_name] = relation_data[field_name]


def _related_entities_for_module(
    module_name: str,
    relations_map: dict[tuple, dict[str, Any]],
) -> list[str]:
    """Return the related entity names for one module."""
    return [
        relation_data["model"]
        for (source_name, _destination_name), relation_data in relations_map.items()
        if source_name == module_name
    ]


def generate_from_blueprint(blueprint: dict[str, Any], output_dir: str | Path) -> None:
    """Generate a NestJS project from an in-memory canonical blueprint."""
    data = coerce_blueprint(blueprint)
    env = _setup_jinja_env()
    base_output_dir = _ensure_output_dir(output_dir)
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


def generate_from_file(source_file: str | Path, output_dir: str | Path) -> None:
    """Generate a NestJS project from a .dsl or YAML blueprint file."""
    source = Path(source_file)
    blueprint = _read_blueprint(str(source))
    generate_from_blueprint(blueprint, output_dir)


def main(blueprint_file: str, nest_project_path: str | Path | None = None) -> None:
    """Backward-compatible file-oriented generator wrapper."""
    generate_from_file(blueprint_file, nest_project_path or "nest_project")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate NestJS code from a blueprint or .dsl file.")
    parser.add_argument("source_file", nargs="?", default="blueprint.yaml")
    parser.add_argument("--output", "-o", default="nest_project")
    args = parser.parse_args()
    generate_from_file(args.source_file, args.output)
