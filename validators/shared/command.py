"""Shared subprocess execution utilities."""

import subprocess
from pathlib import Path
from typing import Optional, Tuple


class SubprocessResult:
    """Result of a subprocess execution."""

    def __init__(self, success: bool, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def run_command(
    command: list, cwd: Path, timeout: int = 60, capture_output: bool = True
) -> SubprocessResult:
    """
    Execute a command and return structured result.

    Args:
        command: Command and arguments as list
        cwd: Working directory for command execution
        timeout: Timeout in seconds
        capture_output: Whether to capture stdout/stderr

    Returns:
        SubprocessResult with execution details
    """
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=capture_output, text=True, timeout=timeout
        )

        return SubprocessResult(
            success=result.returncode == 0,
            stdout=result.stdout if capture_output else "",
            stderr=result.stderr if capture_output else "",
            returncode=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return SubprocessResult(success=False, stderr="Command timeout")
    except FileNotFoundError:
        return SubprocessResult(success=False, stderr=f"Command not found: {command[0]}")
    except Exception as e:
        return SubprocessResult(success=False, stderr=str(e))


def start_process(command: list, cwd: Path) -> subprocess.Popen:
    """
    Start a process without waiting for completion.

    Args:
        command: Command and arguments as list
        cwd: Working directory for command execution

    Returns:
        Popen process object
    """
    return subprocess.Popen(
        command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def terminate_process(process: subprocess.Popen, timeout: int = 5) -> None:
    """
    Safely terminate a process and ensure cleanup.

    Args:
        process: Process to terminate
        timeout: Time to wait before killing
    """
    import time

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()  # Wait for kill to complete

    # Small delay to ensure port is released
    time.sleep(1)


def check_process_running(process: subprocess.Popen) -> Tuple[bool, Optional[str]]:
    """
    Check if a process is still running.

    Args:
        process: Process to check

    Returns:
        Tuple of (is_running, error_output)
    """
    if process.poll() is not None:
        _, stderr = process.communicate()
        return False, stderr
    return True, None
