from pathlib import Path
from typing import Any

from .runtime import validate_runtime
from .syntax import validate_syntactic

RUNTIME_ERROR_PREFIX = "Runtime error during"


def _format_syntactic_errors(result: dict[str, Any]) -> list[str]:
    """Convert syntactic validation results into display strings."""
    if result.get("valid", False):
        return []

    return [
        f"{error.get('file', '?')}:{error.get('line', '?')} - {error.get('message', 'Unknown error')}"
        for error in result.get("errors", [])
    ]


def _runtime_error_message(output: Any) -> str:
    """Extract a displayable message from a runtime error payload."""
    if isinstance(output, dict):
        return output.get("message", str(output))
    return str(output)


def _format_runtime_errors(result: dict[str, Any]) -> list[str]:
    """Convert runtime validation results into display strings."""
    if result.get("valid", False):
        return []

    errors = []
    for stage, output in result.get("errors", {}).items():
        if output:
            message = _runtime_error_message(output)
            errors.append(f"{RUNTIME_ERROR_PREFIX} {stage}: {message[:200]}...")
    return errors


def main(project_path: Path) -> list[str]:
    """Main function to run the validation process.

    Args:
        project_path (Path): The path to the project.

    Returns:
        list[str]: A list of validation errors.
    """
    syntactic_result: dict[str, Any] = validate_syntactic(project_path)
    runtime_result: dict[str, Any] = validate_runtime(project_path)
    return _format_syntactic_errors(syntactic_result) + _format_runtime_errors(runtime_result)


if __name__ == "__main__":
    project_path = Path.cwd()
    errors = main(project_path)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(error)
    else:
        print("No validation errors found.")
