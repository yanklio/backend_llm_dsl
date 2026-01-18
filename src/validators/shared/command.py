import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple


class SubprocessResult:
    """Result of a subprocess execution."""

    def __init__(
        self, success: bool, stdout: str = "", stderr: str = "", returncode: int = 0
    ):
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
        return SubprocessResult(
            success=False, stderr=f"Command not found: {command[0]}"
        )
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


def is_port_in_use(port: int) -> bool:
    """
    Check if a port is currently in use.

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
    """
    Get all PIDs using a specific port.

    Args:
        port: Port number to check

    Returns:
        List of process IDs
    """
    pids = []

    # Try lsof first
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
            return pids
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try fuser as fallback
    try:
        result = subprocess.run(
            ["fuser", f"{port}/tcp"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split()
            return pids
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return pids


def kill_process_on_port(port: int) -> bool:
    """
    Kill any process using the specified port.

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
    """
    Forcefully kill all processes on a port with retries.

    Args:
        port: Port number to kill
        max_attempts: Number of kill attempts

    Returns:
        True if port is now free, False otherwise
    """
    for attempt in range(max_attempts):
        if not is_port_in_use(port):
            return True

        if kill_process_on_port(port):
            return True

        time.sleep(1)

    return not is_port_in_use(port)


def wait_for_port_free(port: int, timeout: int = 10) -> bool:
    """
    Wait for a port to become free.

    Args:
        port: Port number to wait for
        timeout: Maximum seconds to wait

    Returns:
        True if port is free, False if timeout
    """
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
    """
    Terminate process with graceful interrupt signal (Ctrl+C), then cleanup port.

    Args:
        process: Process to terminate
        timeout: Timeout for graceful termination in seconds
        port: Optional port number to force free if needed
        delay_cleanup: Delay in seconds before cleaning up port (simulates Ctrl+C interrupt)

    Returns:
        True if successful, False otherwise
    """
    # Step 1: Send interrupt signal (SIGINT - like Ctrl+C)
    if process.poll() is None:
        try:
            process.send_signal(signal.SIGINT)
        except Exception:
            pass

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Timeout: force kill
            process.kill()
            process.wait()

    # Step 2: Wait for cleanup delay
    if delay_cleanup > 0:
        time.sleep(delay_cleanup)

    # Step 3: Wait for port to naturally free up
    if port is not None:
        wait_for_port_free(port, timeout=5)

        # Step 4: Force kill port if still in use
        if is_port_in_use(port):
            force_kill_port(port)

    return True


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
