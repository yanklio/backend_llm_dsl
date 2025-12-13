"""Runtime validation for NestJS projects."""

from pathlib import Path
from typing import List, Optional

from ..shared.error_types import RuntimeValidationResult
from ..shared.project_utils import validate_project_structure
from .endpoint_tester import test_endpoints
from .npm_commands import run_npm_build, run_npm_install, run_npm_start


def validate_project(
    project_path: str,
    endpoints: Optional[List[str]] = None,
    base_url: str = "http://localhost:3000",
) -> RuntimeValidationResult:
    """
    Validate runtime correctness of a NestJS project.

    Args:
        project_path: Path to NestJS project directory
        endpoints: Optional list of endpoints to test (e.g., ["GET /users", "POST /users"])
        base_url: Base URL of the running application

    Returns:
        RuntimeValidationResult with validation results containing:
        - valid: bool
        - build_success: bool
        - start_success: bool
        - endpoint_tests: Dict with endpoint test results (if endpoints provided)
        - errors: List[Dict] with stage and message
    """
    project_path_obj = Path(project_path)
    errors = []

    # Validate project structure
    structure_error = validate_project_structure(project_path_obj)
    if structure_error:
        errors.append(structure_error)
        return RuntimeValidationResult(
            valid=False,
            build_success=False,
            start_success=False,
            endpoint_tests={},
            errors=errors,
        )

    # Run npm install
    install_result = run_npm_install(project_path_obj)
    if not install_result["success"]:
        errors.append(install_result["error"])
        return RuntimeValidationResult(
            valid=False,
            build_success=False,
            start_success=False,
            endpoint_tests={},
            errors=errors,
        )

    # Run npm build
    build_result = run_npm_build(project_path_obj)
    if not build_result["success"]:
        errors.append(build_result["error"])
        return RuntimeValidationResult(
            valid=False,
            build_success=False,
            start_success=False,
            endpoint_tests={},
            errors=errors,
        )

    # Run npm start
    start_result = run_npm_start(project_path_obj)
    if not start_result["success"]:
        errors.append(start_result["error"])
        return RuntimeValidationResult(
            valid=False,
            build_success=True,
            start_success=False,
            endpoint_tests={},
            errors=errors,
        )

    # Test endpoints if provided
    endpoint_results = {}
    if endpoints:
        endpoint_test = test_endpoints(project_path_obj, endpoints, base_url)
        endpoint_results = endpoint_test["results"]
        if not endpoint_test["success"]:
            errors.extend(endpoint_test["errors"])

    return RuntimeValidationResult(
        valid=len(errors) == 0,
        build_success=True,
        start_success=True,
        endpoint_tests=endpoint_results,
        errors=errors,
    )


__all__ = [
    "validate_project",
    "run_npm_install",
    "run_npm_build",
    "run_npm_start",
    "test_endpoints",
]
