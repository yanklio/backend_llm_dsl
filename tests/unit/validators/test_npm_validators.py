"""Tests for NPM validators."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.validators.runtime_validators.npm_base_commands import (
    _run_npm_build,
    _run_npm_install,
    _run_npm_start,
    check_base_npm,
)
from src.validators.shared.command import SubprocessResult
from src.validators.shared.error_types import ErrorCodes


class TestNpmInstall:
    """Tests for npm install validation."""

    @patch('src.validators.runtime_validators.npm_base_commands.run_command')
    def test_successful_install(self, mock_run_command, temp_dir):
        """Test successful npm install."""
        mock_run_command.return_value = SubprocessResult(
            success=True,
            stdout="added 100 packages",
            stderr="",
            returncode=0
        )

        result = _run_npm_install(temp_dir)
        assert result["success"] is True
        assert "error" not in result

    @patch('src.validators.runtime_validators.npm_base_commands.run_command')
    def test_install_failure(self, mock_run_command, temp_dir):
        """Test npm install failure."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="npm ERR! Failed to install package",
            returncode=1
        )

        result = _run_npm_install(temp_dir)
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.INSTALL_FAILED

    @patch('src.validators.runtime_validators.npm_base_commands.run_command')
    def test_install_timeout(self, mock_run_command, temp_dir):
        """Test npm install timeout."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="Command timeout after 180s",
            returncode=1
        )

        result = _run_npm_install(temp_dir)
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.INSTALL_TIMEOUT
        assert "timeout" in result["error"]["message"].lower()

    @patch('src.validators.runtime_validators.npm_base_commands.run_command')
    def test_npm_not_found(self, mock_run_command, temp_dir):
        """Test npm command not found."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="Command not found: npm",
            returncode=127
        )

        result = _run_npm_install(temp_dir)
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.NPM_NOT_FOUND


class TestNpmBuild:
    """Tests for npm build validation."""

    @patch('src.validators.runtime_validators.npm_base_commands.run_command')
    def test_successful_build(self, mock_run_command, temp_dir):
        """Test successful npm build."""
        mock_run_command.return_value = SubprocessResult(
            success=True,
            stdout="Build completed successfully",
            stderr="",
            returncode=0
        )

        result = _run_npm_build(temp_dir)
        assert result["success"] is True
        assert "error" not in result

    @patch('src.validators.runtime_validators.npm_base_commands.run_command')
    def test_build_failure(self, mock_run_command, temp_dir):
        """Test npm build failure."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="Build failed with errors",
            returncode=1
        )

        result = _run_npm_build(temp_dir)
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.BUILD_FAILED

    @patch('src.validators.runtime_validators.npm_base_commands.run_command')
    def test_build_timeout(self, mock_run_command, temp_dir):
        """Test npm build timeout."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="Command timeout after 120s",
            returncode=1
        )

        result = _run_npm_build(temp_dir)
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.BUILD_TIMEOUT


class TestNpmStart:
    """Tests for npm start validation."""

    @patch('src.validators.runtime_validators.npm_base_commands.terminate_process')
    @patch('src.validators.runtime_validators.npm_base_commands.check_process_running')
    @patch('src.validators.runtime_validators.npm_base_commands.start_process')
    def test_successful_start(self, mock_start, mock_check, mock_terminate, temp_dir):
        """Test successful application start."""
        mock_process = Mock()
        mock_start.return_value = mock_process
        mock_check.return_value = (True, None)

        result = _run_npm_start(temp_dir, wait_time=1, terminate=True, port=3000)
        assert result["success"] is True
        assert "error" not in result
        mock_terminate.assert_called_once()

    @patch('src.validators.runtime_validators.npm_base_commands.check_process_running')
    @patch('src.validators.runtime_validators.npm_base_commands.start_process')
    def test_start_crashed(self, mock_start, mock_check, temp_dir):
        """Test application crashes on start."""
        mock_process = Mock()
        mock_start.return_value = mock_process
        mock_check.return_value = (False, "Application crashed: Error loading module")

        result = _run_npm_start(temp_dir, wait_time=1, terminate=True, port=3000)
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.START_CRASHED
        assert "crashed" in result["error"]["message"].lower()

    @patch('src.validators.runtime_validators.npm_base_commands.start_process')
    def test_start_subprocess_error(self, mock_start, temp_dir):
        """Test subprocess error during start."""
        mock_start.side_effect = subprocess.SubprocessError("Process failed to start")

        result = _run_npm_start(temp_dir, wait_time=1, terminate=True, port=3000)
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.START_ERROR

    @patch('src.validators.runtime_validators.npm_base_commands.check_process_running')
    @patch('src.validators.runtime_validators.npm_base_commands.start_process')
    def test_start_no_terminate(self, mock_start, mock_check, temp_dir):
        """Test starting without terminating process."""
        mock_process = Mock()
        mock_start.return_value = mock_process
        mock_check.return_value = (True, None)

        result = _run_npm_start(temp_dir, wait_time=1, terminate=False, port=3000)
        assert result["success"] is True
        assert "process" in result
        assert result["process"] == mock_process


class TestCheckBaseNpm:
    """Tests for integrated npm checks."""

    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_start')
    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_build')
    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_install')
    def test_all_checks_pass(self, mock_install, mock_build, mock_start, temp_dir):
        """Test when all npm checks pass."""
        mock_install.return_value = {"success": True}
        mock_build.return_value = {"success": True}
        mock_start.return_value = {"success": True}

        result = check_base_npm(temp_dir)
        assert result["install_success"] is True
        assert result["build_success"] is True
        assert result["start_success"] is True
        assert result["errors"] == {}

    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_start')
    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_build')
    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_install')
    def test_install_fails(self, mock_install, mock_build, mock_start, temp_dir):
        """Test when npm install fails."""
        mock_install.return_value = {
            "success": False,
            "error": {"stage": "install", "message": "Install failed", "code": ErrorCodes.INSTALL_FAILED}
        }
        mock_build.return_value = {"success": True}
        mock_start.return_value = {"success": True}

        result = check_base_npm(temp_dir)
        assert result["install_success"] is False
        assert "install" in result["errors"]
        assert result["errors"]["install"]["code"] == ErrorCodes.INSTALL_FAILED

    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_start')
    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_build')
    @patch('src.validators.runtime_validators.npm_base_commands._run_npm_install')
    def test_multiple_failures(self, mock_install, mock_build, mock_start, temp_dir):
        """Test when multiple npm commands fail."""
        mock_install.return_value = {
            "success": False,
            "error": {"stage": "install", "message": "Install failed", "code": ErrorCodes.INSTALL_FAILED}
        }
        mock_build.return_value = {
            "success": False,
            "error": {"stage": "build", "message": "Build failed", "code": ErrorCodes.BUILD_FAILED}
        }
        mock_start.return_value = {"success": True}

        result = check_base_npm(temp_dir)
        assert result["install_success"] is False
        assert result["build_success"] is False
        assert "install" in result["errors"]
        assert "build" in result["errors"]
