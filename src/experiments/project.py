"""Project setup, cleanup, and validation helpers for experiments."""

import shutil
from pathlib import Path
from typing import Any

from src.validators import validate_runtime, validate_syntactic

from .io import SuppressOutput
from .paths import BASE_NEST_PROJECT_DIR

CLEAN_DIRS = ["src", "dist", "data"]
BASE_PROJECT_FILES = {
    "package.json",
    "tsconfig.json",
    "tsconfig.build.json",
    "nest-cli.json",
    "eslint.config.mjs",
}


def _runtime_exception_result(exc: Exception) -> dict[str, Any]:
    """Build a normalized runtime-validation failure payload."""
    return {
        "valid": False,
        "install_success": False,
        "build_success": False,
        "start_success": False,
        "errors": {"runtime": {"message": str(exc)}},
    }


def clean_project(project_path: Path) -> None:
    """Clean generated directories between experiment runs."""
    for directory_name in CLEAN_DIRS:
        directory_path = project_path / directory_name
        if directory_path.exists():
            shutil.rmtree(directory_path)


def ensure_base_project(project_path: Path) -> None:
    """Copy required scaffold files into the generated project directory."""
    if not BASE_NEST_PROJECT_DIR.exists():
        return

    for item in BASE_NEST_PROJECT_DIR.iterdir():
        destination = project_path / item.name
        if item.is_dir() and item.name not in CLEAN_DIRS:
            continue

        if item.is_file() and (not destination.exists() or destination.name in BASE_PROJECT_FILES):
            shutil.copy2(item, destination)


def validate_project(project_path: Path) -> dict[str, Any]:
    """Run syntactic and runtime validation for a generated project."""
    with SuppressOutput():
        try:
            runtime = validate_runtime(str(project_path))
        except Exception as exc:
            runtime = _runtime_exception_result(exc)
        syntactic = validate_syntactic(str(project_path))

    return {
        "syntactic": syntactic,
        "runtime": runtime,
        "overall_valid": syntactic.get("valid", False) and runtime.get("valid", False),
    }
