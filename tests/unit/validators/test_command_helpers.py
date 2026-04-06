"""Tests for command execution helpers."""

import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.validators.shared.command import (
    SubprocessResult,
    check_process_running,
    is_port_in_use,
    run_command,
    wait_for_port_free,
)


class TestSubprocessResult:
    """Tests for SubprocessResult class."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = SubprocessResult(
            success=True,
            stdout="output",
            stderr="",
            returncode=0
        )
        assert result.success is True
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.returncode == 0

    def test_failure_result(self):
        """Test creating a failure result."""
        result = SubprocessResult(
            success=False,
            stdout="",
            stderr="error message",
            returncode=1
        )
        assert result.success is False
        assert result.stderr == "error message"
        assert result.returncode == 1


class TestRunCommand:
    """Tests for run_command function."""

    def test_successful_command(self, temp_dir):
        """Test running a successful command."""
        result = run_command(["echo", "hello"], cwd=temp_dir, timeout=5)
        assert result.success is True
        assert "hello" in result.stdout
        assert result.returncode == 0

    def test_failed_command(self, temp_dir):
        """Test running a command that fails."""
        result = run_command(["ls", "nonexistent_file"], cwd=temp_dir, timeout=5)
        assert result.success is False
        assert result.returncode != 0

    def test_command_timeout(self, temp_dir):
        """Test command timeout handling."""
        # Run a command that will timeout
        result = run_command(["sleep", "10"], cwd=temp_dir, timeout=1)
        assert result.success is False
        assert "timeout" in result.stderr.lower()

    def test_command_not_found(self, temp_dir):
        """Test handling of command not found."""
        result = run_command(["nonexistent_command_xyz"], cwd=temp_dir, timeout=5)
        assert result.success is False
        assert "not found" in result.stderr.lower()

    def test_capture_output_disabled(self, temp_dir):
        """Test running command without capturing output."""
        result = run_command(["echo", "hello"], cwd=temp_dir, timeout=5, capture_output=False)
        assert result.success is True
        assert result.stdout == ""
        assert result.stderr == ""


class TestIsPortInUse:
    """Tests for port checking functions."""

    def test_port_not_in_use(self):
        """Test checking a port that is not in use."""
        # Find a free port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            free_port = s.getsockname()[1]

        assert is_port_in_use(free_port) is False

    def test_port_in_use(self):
        """Test checking a port that is in use."""
        import socket
        # Bind to a port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            used_port = s.getsockname()[1]
            # Port is in use within this context
            assert is_port_in_use(used_port) is True


class TestWaitForPortFree:
    """Tests for wait_for_port_free function."""

    def test_port_already_free(self):
        """Test waiting for a port that is already free."""
        # Find a free port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            free_port = s.getsockname()[1]

        # Should return immediately
        result = wait_for_port_free(port=free_port, timeout=1)
        assert result is True

    def test_port_timeout(self):
        """Test timeout when waiting for a port."""
        # Bind to a port and hold it
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            used_port = s.getsockname()[1]

            # Should timeout while port is held
            result = wait_for_port_free(port=used_port, timeout=1)
            assert result is False


class TestCheckProcessRunning:
    """Tests for check_process_running function."""

    def test_running_process(self):
        """Test checking a process that is still running."""
        # Start a long-running process
        process = subprocess.Popen(["sleep", "5"])
        try:
            is_running, error = check_process_running(process)
            assert is_running is True
            assert error is None
        finally:
            process.kill()
            process.wait()

    def test_terminated_process(self):
        """Test checking a process that has terminated."""
        # Start and immediately terminate a process
        process = subprocess.Popen(["echo", "test"])
        process.wait()

        is_running, error = check_process_running(process)
        assert is_running is False
        # error might be None or empty string depending on the command
