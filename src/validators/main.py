from pathlib import Path
from typing import Any

from .runtime_validators import validate_runtime
from .syntactic_validators import validate_syntactic


def main(project_path: Path) -> list[str]:
    """Main function to run the validation process.

    Args:
        project_path (Path): The path to the project.

    Returns:
        list[str]: A list of validation errors.
    """
    all_errors: list[str] = []

    syn_result: dict[str, Any] = validate_syntactic(project_path)
    if not syn_result.get("valid", False):
        for e in syn_result.get("errors", []):
            msg = f"{e.get('file', '?')}:{e.get('line', '?')} - {e.get('message', 'Unknown error')}"
            all_errors.append(msg)

    run_result: dict[str, Any] = validate_runtime(project_path)
    if not run_result.get("valid", False):
        runtime_errors = run_result.get("errors", {})
        for stage, output in runtime_errors.items():
            if output:
                all_errors.append(f"Runtime error during {stage}: {output[:200]}...")

    return all_errors


if __name__ == "__main__":
    project_path = Path.cwd()
    errors = main(project_path)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(error)
    else:
        print("No validation errors found.")
