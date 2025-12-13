"""Project structure validation utilities."""

from pathlib import Path
from typing import Dict, Optional

from .error_types import ErrorCodes, ValidationError, create_error


def validate_project_structure(project_path: Path) -> Optional[ValidationError]:
    """
    Validate basic project structure exists.

    Args:
        project_path: Path to the project directory

    Returns:
        ValidationError if structure is invalid, None otherwise
    """
    if not project_path.exists():
        return create_error(
            "setup",
            f"Project directory not found: {project_path}",
            ErrorCodes.MISSING_SRC,
        )

    if not (project_path / "package.json").exists():
        return create_error("setup", "package.json not found", ErrorCodes.MISSING_PACKAGE_JSON)

    return None


def validate_source_directory(project_path: Path) -> Dict:
    """
    Validate source directory and count TypeScript files.

    Args:
        project_path: Path to the project directory

    Returns:
        Dictionary with src_exists, ts_files_count, and optional error
    """
    src_path = project_path / "src"

    if not src_path.exists():
        return {
            "src_exists": False,
            "ts_files_count": 0,
            "error": create_error(
                "setup",
                f"Source directory not found: {src_path}",
                ErrorCodes.MISSING_SRC,
            ),
        }

    ts_files = list(src_path.rglob("*.ts"))
    ts_files_count = len(ts_files)

    if ts_files_count == 0:
        return {
            "src_exists": True,
            "ts_files_count": 0,
            "error": create_error("setup", "No TypeScript files found", ErrorCodes.NO_FILES),
        }

    return {"src_exists": True, "ts_files_count": ts_files_count, "error": None}


def validate_typescript_config(project_path: Path) -> Optional[ValidationError]:
    """
    Validate TypeScript configuration exists.

    Args:
        project_path: Path to the project directory

    Returns:
        ValidationError if config is missing, None otherwise
    """
    if not (project_path / "tsconfig.json").exists():
        return create_error("setup", "tsconfig.json not found", ErrorCodes.MISSING_CONFIG)

    return None


def get_project_paths(project_path: str) -> Dict[str, Path]:
    """
    Get common project paths as Path objects.

    Args:
        project_path: Path to the project directory as string

    Returns:
        Dictionary with common paths (root, src, package_json, tsconfig)
    """
    root = Path(project_path)

    return {
        "root": root,
        "src": root / "src",
        "package_json": root / "package.json",
        "tsconfig": root / "tsconfig.json",
    }
