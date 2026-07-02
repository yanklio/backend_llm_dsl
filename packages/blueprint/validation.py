"""Structural validation for canonical YAML blueprint dictionaries."""

from typing import Any

from packages.shared.exceptions import ConfigurationException


def validate_blueprint_structure(blueprint: dict[str, Any]) -> dict[str, Any]:
    """Validate only the top-level canonical blueprint shape."""
    root = blueprint.get("root")
    modules = blueprint.get("modules")
    if not isinstance(root, dict):
        raise ConfigurationException("Blueprint root must be a dictionary", code="CONFIG004")
    if not isinstance(modules, list):
        raise ConfigurationException("Blueprint modules must be a list", code="CONFIG004")
    return blueprint
