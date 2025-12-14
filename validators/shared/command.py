"""Shared subprocess execution utilities."""

import socket
import subprocess
import time
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


def terminate_process(
    process: subprocess.Popen, timeout: int = 5, port: Optional[int] = None
) -> None:
    """
    Safely terminate a process and ensure cleanup.

    Args:
        process: Process to terminate
        timeout: Time to wait before killing
        port: Optional port number to wait for release (e.g., 3000 for NestJS)
    """
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    time.sleep(2)

    if port is not None:
        wait_for_port_release(port, max_wait=10)
    else:
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


def wait_for_port_release(port: int, max_wait: int = 10) -> bool:
    """
    Wait for a port to be released.

    Args:
        port: Port number to wait for
        max_wait: Maximum seconds to wait

    Returns:
        True if port was released, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if not is_port_in_use(port):
            return True
        time.sleep(0.5)
    return False


def kill_process_on_port(port: int) -> bool:
    """
    Kill any process using the specified port.

    Args:
        port: Port number to free up

    Returns:
        True if successful, False otherwise
    """
    try:
        result = subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
        time.sleep(2)
        return not is_port_in_use(port)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-9", pid], timeout=5)
                    except:
                        pass
                time.sleep(2)
                return not is_port_in_use(port)
        except:
            pass
    return False
