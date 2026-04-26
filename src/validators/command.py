"""Command execution utilities for validators.

Provides helpers for running subprocesses, managing ports, and handling
process lifecycle during validation.
"""

import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from src.shared.config import get_config

PORT_PID_COMMANDS = [
    ["lsof", "-ti"],
    ["fuser"],
]


class SubprocessResult:
    """Result of a subprocess execution."""

    def __init__(self, success: bool, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _run_port_pid_command(command: list[str], port: int) -> subprocess.CompletedProcess[str] | None:
    """Run a command that may report process IDs for a port."""
    port_arg = f":{port}" if command[0] == "lsof" else f"{port}/tcp"

    try:
        return subprocess.run(
            [*command, port_arg],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _parse_port_pids(command_name: str, stdout: str) -> list[str]:
    """Parse process IDs returned by a port lookup command."""
    if not stdout.strip():
        return []
    if command_name == "lsof":
        return [pid.strip() for pid in stdout.strip().split("\n") if pid.strip()]
    return stdout.strip().split()


def _wait_for_process_exit(process: subprocess.Popen, timeout: int) -> None:
    """Wait for process exit and force kill on timeout."""
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _send_interrupt(process: subprocess.Popen) -> None:
    """Send SIGINT to a running process, ignoring signal errors."""
    try:
        process.send_signal(signal.SIGINT)
    except Exception:
        pass


def _cleanup_port(port: int) -> None:
    """Wait for a port to free up and force cleanup if needed."""
    wait_for_port_free(port, timeout=5)
    if is_port_in_use(port):
        force_kill_port(port)


def run_command(
    command: list, cwd: Path, timeout: Optional[int] = None, capture_output: bool = True
) -> SubprocessResult:
    """Execute a command and return structured result.

    Args:
        command: Command and arguments as list
        cwd: Working directory for command execution
        timeout: Timeout in seconds (uses config default if None)
        capture_output: Whether to capture stdout/stderr

    Returns:
        SubprocessResult with execution details

    Raises:
        ValidationTimeoutException: If command times out (wrapped in SubprocessResult)
    """
    if timeout is None:
        config = get_config()
        timeout = config.validation.tsc_timeout

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
        return SubprocessResult(success=False, stderr=f"Command timeout after {timeout}s")
    except FileNotFoundError:
        return SubprocessResult(success=False, stderr=f"Command not found: {command[0]}")
    except (OSError, subprocess.SubprocessError) as e:
        return SubprocessResult(success=False, stderr=f"Subprocess error: {e}")
    except Exception as e:
        return SubprocessResult(success=False, stderr=f"Unexpected error: {e}")


def start_process(command: list, cwd: Path) -> subprocess.Popen:
    """Start a process without waiting for completion.

    Args:
        command: Command and arguments as list
        cwd: Working directory for command execution

    Returns:
        Popen process object
    """
    return subprocess.Popen(
        command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def is_port_in_use(port: int) -> bool:
    """Check if a port is currently in use.

    Args:
        port: Port number to check

    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return False
        except OSError:
            return True


def get_pids_on_port(port: int) -> list:
    """Get all PIDs using a specific port.

    Args:
        port: Port number to check

    Returns:
        List of process IDs
    """
    for command in PORT_PID_COMMANDS:
        result = _run_port_pid_command(command, port)
        if result is None or result.returncode != 0:
            continue

        pids = _parse_port_pids(command[0], result.stdout)
        if pids:
            return pids

    return []


def kill_process_on_port(port: int) -> bool:
    """Kill any process using the specified port.

    Args:
        port: Port number to free up

    Returns:
        True if port is now free, False otherwise
    """
    # Check if already free
    if not is_port_in_use(port):
        return True

    # Get PIDs and kill them
    pids = get_pids_on_port(port)

    for pid in pids:
        try:
            subprocess.run(["kill", "-9", pid], timeout=2)
        except Exception:
            pass

    time.sleep(1)
    return not is_port_in_use(port)


def force_kill_port(port: int, max_attempts: int = 3) -> bool:
    """Forcefully kill all processes on a port with retries.

    Args:
        port: Port number to kill
        max_attempts: Number of kill attempts

    Returns:
        True if port is now free, False otherwise
    """
    for _ in range(max_attempts):
        if not is_port_in_use(port):
            return True

        if kill_process_on_port(port):
            return True

        time.sleep(1)

    return not is_port_in_use(port)


def wait_for_port_free(port: Optional[int] = None, timeout: Optional[int] = None) -> bool:
    """Wait for a port to become free.

    Args:
        port: Port number to wait for (uses config default if None)
        timeout: Maximum seconds to wait (uses config default if None)

    Returns:
        True if port is free, False if timeout
    """
    config = get_config()
    if port is None:
        port = config.validation.app_port
    if timeout is None:
        timeout = config.validation.port_wait_time

    start_time = time.time()

    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            return True
        time.sleep(0.5)

    return False


def terminate_process(
    process: subprocess.Popen,
    timeout: int = 5,
    port: Optional[int] = None,
    delay_cleanup: float = 0,
) -> bool:
    """Terminate process with graceful interrupt signal (Ctrl+C), then cleanup port.

    Args:
        process: Process to terminate
        timeout: Timeout for graceful termination in seconds
        port: Optional port number to force free if needed
        delay_cleanup: Delay in seconds before cleaning up port (simulates Ctrl+C interrupt)

    Returns:
        True if successful, False otherwise
    """
    if process.poll() is None:
        _send_interrupt(process)
        _wait_for_process_exit(process, timeout)

    if delay_cleanup > 0:
        time.sleep(delay_cleanup)

    if port is not None:
        _cleanup_port(port)

    return True


def check_process_running(process: subprocess.Popen) -> tuple[bool, Optional[str]]:
    """Check if a process is still running.

    Args:
        process: Process to check

    Returns:
        Tuple of (is_running, error_output)
    """
    if process.poll() is not None:
        _, stderr = process.communicate()
        return False, stderr
    return True, None
