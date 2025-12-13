"""NPM command execution utilities for runtime validation."""

from pathlib import Path
from typing import Dict

from ..shared.error_types import ErrorCodes, create_error
from ..shared.subprocess_utils import run_command


def run_npm_install(project_path: Path) -> Dict:
    """
    Install npm dependencies.

    Args:
        project_path: Path to the NestJS project

    Returns:
        Dictionary with success status and optional error
    """
    result = run_command(["npm", "install"], cwd=project_path, timeout=300)

    if not result.success:
        error_message = result.stderr[:200] if result.stderr else "npm install failed"

        if "not found" in error_message.lower():
            code = ErrorCodes.NPM_NOT_FOUND
            message = "npm not found"
        elif "timeout" in error_message.lower():
            code = ErrorCodes.INSTALL_TIMEOUT
            message = "npm install timeout"
        else:
            code = ErrorCodes.INSTALL_FAILED
            message = f"npm install failed: {error_message}"

        return {"success": False, "error": create_error("install", message, code)}

    return {"success": True}


def run_npm_build(project_path: Path) -> Dict:
    """
    Build the NestJS project.

    Args:
        project_path: Path to the NestJS project

    Returns:
        Dictionary with success status and optional error
    """
    result = run_command(["npm", "run", "build"], cwd=project_path, timeout=120)

    if not result.success:
        error_message = result.stderr[:200] if result.stderr else "Build failed"

        if "timeout" in error_message.lower():
            code = ErrorCodes.BUILD_TIMEOUT
            message = "Build timeout"
        else:
            code = ErrorCodes.BUILD_FAILED
            message = f"npm run build failed: {error_message}"

        return {"success": False, "error": create_error("build", message, code)}

    return {"success": True}


def run_npm_start(project_path: Path, wait_time: int = 5) -> Dict:
    """
    Start the application and verify it runs.

    Args:
        project_path: Path to the NestJS project
        wait_time: Seconds to wait before checking if app crashed

    Returns:
        Dictionary with success status and optional error
    """
    import time

    from ..shared.subprocess_utils import check_process_running, start_process, terminate_process

    try:
        process = start_process(["npm", "run", "start"], cwd=project_path)
        time.sleep(wait_time)

        is_running, error_output = check_process_running(process)

        if not is_running:
            error_message = error_output[:200] if error_output else "Application crashed"
            return {
                "success": False,
                "error": create_error(
                    "start", f"Application crashed: {error_message}", ErrorCodes.START_CRASHED
                ),
            }

        terminate_process(process)
        return {"success": True}

    except Exception as e:
        return {
            "success": False,
            "error": create_error("start", f"Start error: {str(e)}", ErrorCodes.START_ERROR),
        }
