"""Load canonical YAML blueprint dictionaries from files or memory."""

from pathlib import Path
from typing import Any

import yaml

from packages.shared.exceptions import ConfigurationException

from .validation import validate_blueprint_structure


def coerce_blueprint(value: dict[str, Any]) -> dict[str, Any]:
    """Accept an already compiled blueprint dictionary."""
    if not isinstance(value, dict):
        raise ConfigurationException("Blueprint must be a YAML dictionary", code="CONFIG004")
    return validate_blueprint_structure(value)


def load_blueprint(path: str | Path) -> dict[str, Any]:
    """Load and structurally validate a YAML blueprint file."""
    source = Path(path)
    try:
        data = yaml.safe_load(source.read_text())
    except FileNotFoundError as exc:
        raise ConfigurationException(f"Blueprint file not found: {source}", code="CONFIG001") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationException(f"Invalid YAML in blueprint file: {exc}", code="CONFIG002") from exc
    return coerce_blueprint(data)
