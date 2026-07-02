"""NPM base command validators."""

import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from packages.shared import logger
from packages.shared.config import get_config
from packages.validator.command import (
    check_process_running,
    run_command,
    start_process,
    terminate_process,
)
from packages.validator.error_types import ErrorCodes, create_error


def _success_result(**extra: Any) -> dict[str, Any]:
    """Create a success payload for runtime checks."""
    return {"success": True, **extra}


def _failure_result(stage: str, message: str, code: str) -> dict[str, Any]:
    """Create a failure payload for runtime checks."""
    logger.warn(message)
    return {"success": False, "error": create_error(stage, message, code)}


def _run_npm_command(
    project_path: Path,
    *,
    stage: str,
    command: list[str],
    timeout: int,
    success_message: str,
    failure_message: str,
    classify_error: Any,
) -> dict[str, Any]:
    """Run one npm command and normalize its success or failure payload."""
    logger.debug(f"Running {' '.join(command)}...")
    result = run_command(command, cwd=project_path, timeout=timeout)

    if result.success:
        logger.success(success_message)
        return _success_result()

    error_message = result.stderr[:200] if result.stderr else failure_message
    code, message = classify_error(error_message)
    return _failure_result(stage, message, code)


def _resolve_start_options(
    wait_time: Optional[int],
    port: Optional[int],
) -> tuple[int, int]:
    """Resolve runtime config defaults for app start validation."""
    config = get_config()
    return (
        config.validation.port_wait_time if wait_time is None else wait_time,
        config.validation.app_port if port is None else port,
    )


def _start_process_or_error(project_path: Path) -> subprocess.Popen:
    """Start the app process for runtime validation."""
    return start_process(["npm", "run", "start"], cwd=project_path)


def _check_startup_result(process: subprocess.Popen) -> str | None:
    """Return an error message if the app crashed during startup."""
    is_running, error_output = check_process_running(process)
    if is_running:
        return None
    return error_output or "Application crashed"


def _handle_started_process(
    process: subprocess.Popen,
    terminate: bool,
    port: int,
) -> dict[str, Any]:
    """Return the correct success payload after a successful start."""
    logger.success("Application started successfully")
    if terminate:
        terminate_process(process, port=port)
        return _success_result()
    return _success_result(process=process)


def _run_stage_checks(project_path: Path) -> dict[str, dict[str, Any]]:
    """Execute install, build, and start checks in order."""
    return {
        "install": _run_npm_install(project_path),
        "build": _run_npm_build(project_path),
        "start": _run_npm_start(project_path),
    }


def validate_runtime(project_path: Path) -> dict[str, Any]:
    """Validate runtime behavior for the generated project.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, Any]: Structured runtime validation result.
    """
    results = check_base_npm(project_path)
    install_success = results["install_success"]
    build_success = results["build_success"]
    start_success = results["start_success"]

    return {
        "valid": install_success and build_success and start_success,
        "install_success": install_success,
        "build_success": build_success,
        "start_success": start_success,
        "errors": results["errors"],
    }


def check_base_npm(project_path: Path) -> dict[str, Any]:
    """Check all base npm commands.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, Any]: Dictionary with success status and errors.
    """
    stage_results = _run_stage_checks(project_path)
    errors = {stage_name: result["error"] for stage_name, result in stage_results.items() if "error" in result}

    return {
        "install_success": stage_results["install"]["success"],
        "build_success": stage_results["build"]["success"],
        "start_success": stage_results["start"]["success"],
        "errors": errors,
    }


def _classify_install_error(error_message: str) -> tuple[str, str]:
    """Map npm install stderr to a normalized error code and message."""
    if "not found" in error_message.lower():
        return ErrorCodes.NPM_NOT_FOUND, "npm not found"
    if "timeout" in error_message.lower():
        return ErrorCodes.INSTALL_TIMEOUT, "npm install timeout"
    return ErrorCodes.INSTALL_FAILED, f"npm install failed: {error_message}"


def _classify_build_error(error_message: str) -> tuple[str, str]:
    """Map npm build stderr to a normalized error code and message."""
    if "timeout" in error_message.lower():
        return ErrorCodes.BUILD_TIMEOUT, "Build timeout"
    return ErrorCodes.BUILD_FAILED, f"npm run build failed: {error_message}"


def _run_npm_install(project_path: Path) -> dict[str, Any]:
    """Install npm dependencies.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, Any]: Dictionary with success status and optional error.
    """
    config = get_config()
    return _run_npm_command(
        project_path,
        stage="install",
        command=["npm", "install", "--legacy-peer-deps"],
        timeout=config.validation.npm_install_timeout,
        success_message="npm install completed",
        failure_message="npm install failed",
        classify_error=_classify_install_error,
    )


def _run_npm_build(project_path: Path) -> dict[str, Any]:
    """Build the NestJS project.

    Args:
        project_path (Path): Path to the NestJS project.

    Returns:
        dict[str, Any]: Dictionary with success status and optional error.
    """
    config = get_config()
    return _run_npm_command(
        project_path,
        stage="build",
        command=["npm", "run", "build"],
        timeout=config.validation.tsc_timeout,
        success_message="Build completed",
        failure_message="Build failed",
        classify_error=_classify_build_error,
    )


def _run_npm_start(
    project_path: Path,
    wait_time: Optional[int] = None,
    terminate: bool = True,
    port: Optional[int] = None,
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
    wait_time, port = _resolve_start_options(wait_time, port)

    try:
        logger.debug(f"Starting application on port {port}...")
        process = _start_process_or_error(project_path)
        time.sleep(wait_time)

        error_message = _check_startup_result(process)
        if error_message is not None:
            logger.error(f"Application crashed: {error_message}")
            return _failure_result(
                "start",
                f"Application crashed: {error_message}",
                ErrorCodes.START_CRASHED,
            )

        return _handle_started_process(process, terminate, port)

    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"Start error: {str(e)}")
        return _failure_result(
            "start",
            f"Start subprocess error: {str(e)}",
            ErrorCodes.START_ERROR,
        )
    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        return _failure_result(
            "start",
            f"Unexpected start error: {str(e)}",
            ErrorCodes.START_ERROR,
        )
