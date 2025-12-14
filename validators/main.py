import Path

from .syntatic_validators import validate_syntatic


def main(project_path: Path):
    """Main function to run the validation process.
    Args:
        project_path (Path): The path to the project.
    Returns:
        List[ValidationError]: A list of validation errors.
    """
    errors = []
    errors.extend(validate_syntatic(project_path))
    return errors


if __name__ == "__main__":
    project_path = Path.cwd()
    errors = main(project_path)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(error)
    else:
        print("No validation errors found.")
