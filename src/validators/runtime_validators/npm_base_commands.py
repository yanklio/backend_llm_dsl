"""NPM base command validators."""

import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from src.shared import logger
from src.shared.config import get_config
from src.shared.exceptions import ValidationException
from src.validators.shared.command import (
    check_process_running,
    run_command,
    start_process,
    terminate_process,
)
from src.validators.shared.error_types import ErrorCodes, create_error


def check_base_npm(project_path: Path) -> dict[str, Any]:
    """Check all base npm commands.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, Any]: Dictionary with success status and errors.
    """
    errors = {}
    install = _run_npm_install(project_path)
    if "error" in install:
        errors["install"] = install["error"]
    build = _run_npm_build(project_path)
    if "error" in build:
        errors["build"] = build["error"]
    start = _run_npm_start(project_path)
    if "error" in start:
        errors["start"] = start["error"]
    return {
        "install_success": install["success"],
        "build_success": build["success"],
        "start_success": start["success"],
        "errors": errors,
    }


def _run_npm_install(project_path: Path) -> dict[str, Any]:
    """Install npm dependencies.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, Any]: Dictionary with success status and optional error.
    """
    config = get_config()
    logger.debug("Running npm install...")
    result = run_command(
        ["npm", "install", "--legacy-peer-deps"],
        cwd=project_path,
        timeout=config.validation.npm_install_timeout
    )

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

        logger.warn(message)

        return {"success": False, "error": create_error("install", message, code)}

    logger.success("npm install completed")
    return {"success": True}


def _run_npm_build(project_path: Path) -> dict[str, Any]:
    """Build the NestJS project.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, Any]: Dictionary with success status and optional error.
    """
    config = get_config()
    logger.debug("Running npm run build...")
    result = run_command(
        ["npm", "run", "build"],
        cwd=project_path,
        timeout=config.validation.tsc_timeout
    )

    if not result.success:
        error_message = result.stderr[:200] if result.stderr else "Build failed"

        if "timeout" in error_message.lower():
            code = ErrorCodes.BUILD_TIMEOUT
            message = "Build timeout"
        else:
            code = ErrorCodes.BUILD_FAILED
            message = f"npm run build failed: {error_message}"

        logger.warn(message)
        return {"success": False, "error": create_error("build", message, code)}

    logger.success("Build completed")
    return {"success": True}


def _run_npm_start(
    project_path: Path,
    wait_time: Optional[int] = None,
    terminate: bool = True,
    port: Optional[int] = None
) -> dict[str, Any]:
    """Start the application and verify it runs.

    Args:
        project_path (Path): Path to the NestJS project.
        wait_time (int): Seconds to wait before checking if app crashed (uses config default if None).
        terminate (bool): Whether to terminate the process after verification.
        port (int): Port number the application runs on (uses config default if None).

    Returns:
        Dict[str, Any]: Dictionary with success status, optional error, and process.
    """
    config = get_config()
    if wait_time is None:
        wait_time = config.validation.port_wait_time
    if port is None:
        port = config.validation.app_port

    try:
        logger.debug(f"Starting application on port {port}...")

        process = start_process(["npm", "run", "start"], cwd=project_path)
        time.sleep(wait_time)

        is_running, error_output = check_process_running(process)

        if not is_running:
            error_message = error_output if error_output else "Application crashed"
            logger.error(f"Application crashed: {error_message}")
            return {
                "success": False,
                "error": create_error(
                    "start",
                    f"Application crashed: {error_message}",
                    ErrorCodes.START_CRASHED,
                ),
            }

        logger.success("Application started successfully")

        if terminate:
            terminate_process(process, port=port)
            return {"success": True}
        else:
            return {"success": True, "process": process}

    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"Start error: {str(e)}")
        return {
            "success": False,
            "error": create_error("start", f"Start subprocess error: {str(e)}", ErrorCodes.START_ERROR),
        }
    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        return {
            "success": False,
            "error": create_error("start", f"Unexpected start error: {str(e)}", ErrorCodes.START_ERROR),
        }
