from .npm_base_commands import check_base_npm


def validate_runtime(project_path):
    """Validate runtime errors in the project.

    Args:
        project_path (str or Path): The path to the project.

    Returns:
        dict: A dictionary containing validation results with keys:
            - valid (bool): Whether all npm operations succeeded
            - install_success (bool): Whether npm install succeeded
            - build_success (bool): Whether npm build succeeded
            - start_success (bool): Whether npm start succeeded
            - errors (dict): Dictionary of errors from install, build, and start operations
    """
    results = check_base_npm(project_path)
    install_result = results["install"]
    build_result = results["build"]
    start_result = results["start"]

    install_success = install_result.get("success", False)
    build_success = build_result.get("success", False)
    start_success = start_result.get("success", False)

    return {
        "valid": install_success and build_success and start_success,
        "install_success": install_success,
        "build_success": build_success,
        "start_success": start_success,
        "errors": results["errors"],
    }


__all__ = ["check_base_npm", "validate_runtime"]
