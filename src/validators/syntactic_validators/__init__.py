from .typescript import check_typescript


def validate_syntactic(project_path):
    """Validate syntactic errors in the project.

    Args:
        project_path (str or Path): The path to the project.

    Returns:
        dict: A dictionary containing validation results with keys:
            - valid (bool): Whether the project has no syntax errors
            - total_files (int): Number of files checked
            - error_count (int): Number of errors found
            - errors (list): List of error details
    """
    errors = check_typescript(project_path)

    return {
        "valid": len(errors) == 0,
        "total_files": 1,  # TypeScript check covers all TS files
        "error_count": len(errors),
        "errors": [
            {
                "file": error.get("file", "unknown"),
                "line": error.get("line", 0),
                "column": error.get("column", 0),
                "message": error.get("message", ""),
                "code": error.get("code", ""),
            }
            for error in errors
        ],
    }


__all__ = ["check_typescript", "validate_syntactic"]
