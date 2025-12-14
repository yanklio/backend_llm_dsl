import time
from pathlib import Path
from typing import Dict

from ..shared.command import check_process_running, run_command, start_process, terminate_process
from ..shared.error_types import ErrorCodes, create_error


def check_base_npm(project_path: Path) -> Dict:
    """
    Check all base npm commmands
    """
    errors = []
    installErrors = _run_npm_install(project_path)
    errors.extend(installErrors)
    buildErrors = _run_npm_build(project_path)
    errors.extend(buildErrors)
    startErrors = _run_npm_start(project_path)
    errors.extend(startErrors)
    return {"install": installErrors, "build": buildErrors, "start": startErrors, "errors": errors}


def _run_npm_install(project_path: Path) -> Dict:
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


def _run_npm_build(project_path: Path) -> Dict:
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


def _run_npm_start(project_path: Path, wait_time: int = 10, terminate: bool = True) -> Dict:
    """
    Start the application and verify it runs.

    Args:
        project_path: Path to the NestJS project
        wait_time: Seconds to wait before checking if app crashed
        terminate: Whether to terminate the process after verification (False if endpoints will be tested)

    Returns:
        Dictionary with success status, optional error, and process if not terminated
    """
    try:
        process = start_process(["npm", "run", "start"], cwd=project_path)
        time.sleep(wait_time)

        is_running, error_output = check_process_running(process)

        if not is_running:
            error_message = error_output if error_output else "Application crashed"
            return {
                "success": False,
                "error": create_error(
                    "start", f"Application crashed: {error_message}", ErrorCodes.START_CRASHED
                ),
            }

        if terminate:
            terminate_process(process)
            return {"success": True}
        else:
            return {"success": True, "process": process}

    except Exception as e:
        return {
            "success": False,
            "error": create_error("start", f"Start error: {str(e)}", ErrorCodes.START_ERROR),
        }
