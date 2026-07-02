"""Blueprint-backed normalized IR loading and validation."""

from pathlib import Path
from typing import Any

import yaml

from packages.generator_nestjs.core.modules.relation import handle_relations
from packages.generator_nestjs.generate import _enrich_modules_with_relations
from packages.dsl_core.compiler import compile_file
from packages.shared.exceptions import ConfigurationException

BlueprintIR = dict[str, Any]


def load_ir(source_file: str | Path) -> BlueprintIR:
    """Load textual DSL or YAML DSL into a normalized blueprint IR."""
    source_path = Path(source_file)
    try:
        if source_path.suffix == ".dsl":
            data = compile_file(source_path)
        else:
            data = yaml.safe_load(source_path.read_text())
    except FileNotFoundError as exc:
        raise ConfigurationException(
            f"Input file not found: {source_path}",
            code="IR001",
            context={"file": str(source_path)},
        ) from exc
    except yaml.YAMLError as exc:
        raise ConfigurationException(
            f"Invalid YAML input: {exc}",
            code="IR002",
            context={"file": str(source_path), "error": str(exc)},
        ) from exc
    except Exception as exc:
        raise ConfigurationException(
            f"Failed to load IR: {exc}",
            code="IR003",
            context={"file": str(source_path), "error": str(exc)},
        ) from exc

    return validate_ir(data)


def validate_ir(data: Any) -> BlueprintIR:
    """Validate and normalize a blueprint-like dictionary into IR."""
    if not isinstance(data, dict):
        raise ConfigurationException(
            "IR must be a dictionary",
            code="IR004",
            context={"type": type(data).__name__},
        )

    modules_data = data.get("modules", [])
    if not isinstance(modules_data, list):
        raise ConfigurationException(
            "IR modules must be a list",
            code="IR005",
            context={"type": type(modules_data).__name__},
        )

    relations_map = handle_relations(modules_data)
    _enrich_modules_with_relations(modules_data, relations_map)
    data["relations"] = relations_map
    return data
