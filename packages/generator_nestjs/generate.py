"""Generate NestJS code from canonical blueprint dictionaries or files."""

import argparse
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from packages.blueprint import coerce_blueprint, load_blueprint
from packages.dsl_core.compiler import compile_file
from packages.shared.exceptions import ConfigurationException
from packages.shared.logger import logger

from .core.modules.module import generate_module
from .core.modules.relation import handle_relations
from .core.root import generate_root_module
from .utils.ts_types import to_ts_type

RELATION_COPY_FIELDS = ["inverseField", "joinTable", "joinColumn"]
ROOT_REQUIRED_FILES = ["app.module.ts", "main.ts", "app.controller.ts", "app.service.ts"]


def _reject_unsafe_path_component(value: str, field_name: str) -> None:
    """Reject blueprint values that could escape the selected output directory."""
    candidate = Path(value)
    if not value or "\\" in value or candidate.is_absolute() or candidate.name != value or value in {".", ".."}:
        raise ConfigurationException(
            f"Unsafe generated path component for {field_name}: {value}",
            code="CONFIG005",
            context={field_name: value},
        )


def _resolve_safe_output_dir(output_dir: str | Path | None = None) -> Path:
    """Resolve a user-provided absolute or relative output directory."""
    requested = Path(output_dir or "nest_project")
    if ".." in requested.parts:
        raise ConfigurationException(
            f"Unsafe output directory: {requested}",
            code="CONFIG005",
            context={"output_dir": str(requested)},
        )

    project_root = Path.cwd().resolve()
    resolved = requested.resolve() if requested.is_absolute() else (project_root / requested).resolve()
    if not requested.is_absolute() and project_root != resolved and project_root not in resolved.parents:
        raise ConfigurationException(
            f"Output directory escapes project root: {requested}",
            code="CONFIG005",
            context={"output_dir": str(requested)},
        )
    return resolved


def _validate_generated_paths(modules_data: list[dict[str, Any]]) -> None:
    """Validate blueprint-derived file path components before rendering files."""
    for module_data in modules_data:
        module_name = str(module_data.get("name", ""))
        _reject_unsafe_path_component(module_name.lower(), "module.name")
        for file_key in module_data.get("generate", []):
            _reject_unsafe_path_component(str(file_key), "module.generate")


def _required_generated_files(data: dict[str, Any], output_dir: Path) -> list[Path]:
    """Return deterministic files that must exist after rendering."""
    src_dir = output_dir / "src"
    required = [src_dir / file_name for file_name in ROOT_REQUIRED_FILES]
    if "database" in data.get("root", {}):
        required.append(src_dir / "database.config.ts")
    for module_data in data.get("modules", []):
        module_lower = str(module_data["name"]).lower()
        module_dir = src_dir / module_lower
        for file_key in module_data.get("generate", []):
            if file_key == "dto":
                required.extend(
                    [
                        module_dir / "dto" / f"create-{module_lower}.dto.ts",
                        module_dir / "dto" / f"update-{module_lower}.dto.ts",
                    ]
                )
            elif file_key == "entity":
                required.append(module_dir / "entities" / f"{module_lower}.entity.ts")
            else:
                required.append(module_dir / f"{module_lower}.{file_key}.ts")
    return required


def _assert_required_files_exist(paths: list[Path]) -> None:
    """Fail generation if any requested deterministic file is missing."""
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise ConfigurationException(
            f"Generation incomplete; missing requested files: {', '.join(missing)}",
            code="CONFIG006",
            context={"missing_files": missing},
        )


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
    """Ensure a safe output directory exists under the current working tree."""
    base_output_dir = _resolve_safe_output_dir(output_dir)
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
    root_config = data.get("root", {})
    modules_data = data.get("modules", [])
    if not modules_data:
        logger.warn("No modules defined in blueprint!")
        return
    _validate_generated_paths(modules_data)
    base_output_dir = _ensure_output_dir(output_dir)
    relations_map = handle_relations(modules_data)
    _enrich_modules_with_relations(modules_data, relations_map)
    generate_root_module(root_config, modules_data, env, base_output_dir)
    src_dir = base_output_dir / "src"
    for module_data in modules_data:
        generate_module(module_data, env, src_dir)
    _assert_required_files_exist(_required_generated_files(data, base_output_dir))
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
