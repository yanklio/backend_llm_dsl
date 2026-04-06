"""Tests for TypeScript validator."""

from unittest.mock import patch

from src.validators.shared.command import SubprocessResult
from src.validators.shared.error_types import ErrorCodes
from src.validators.syntactic_validators.typescript import check_typescript


class TestCheckTypescript:
    """Tests for check_typescript function."""

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_successful_compilation(self, mock_run_command, temp_dir):
        """Test successful TypeScript compilation with no errors."""
        mock_run_command.return_value = SubprocessResult(
            success=True,
            stdout="",
            stderr="",
            returncode=0
        )

        errors = check_typescript(temp_dir)
        assert errors == []
        mock_run_command.assert_called_once_with(
            ["npx", "tsc", "--noEmit"],
            cwd=temp_dir,
            timeout=60
        )

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_typescript_compilation_errors(self, mock_run_command, temp_dir):
        """Test TypeScript compilation with syntax errors."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="src/app.ts(10,5): error TS2304: Cannot find name 'foo'.\n"
                   "src/utils.ts(20,10): error TS2322: Type 'string' is not assignable to type 'number'.",
            stderr="",
            returncode=1
        )

        errors = check_typescript(temp_dir)
        assert len(errors) == 2
        assert errors[0]["file"] == "src/app.ts"
        assert errors[0]["line"] == 10
        assert "Cannot find name 'foo'" in errors[0]["message"]

        assert errors[1]["file"] == "src/utils.ts"
        assert errors[1]["line"] == 20
        assert "Type 'string' is not assignable to type 'number'" in errors[1]["message"]

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_typescript_timeout(self, mock_run_command, temp_dir):
        """Test TypeScript compilation timeout."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="Command timeout after 60s",
            returncode=1
        )

        errors = check_typescript(temp_dir)
        assert len(errors) == 1
        assert errors[0]["stage"] == "compile"
        assert "timeout" in errors[0]["message"].lower()
        assert errors[0]["code"] == ErrorCodes.TIMEOUT

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_typescript_not_found(self, mock_run_command, temp_dir):
        """Test TypeScript compiler not found."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="Command not found: npx",
            returncode=127
        )

        errors = check_typescript(temp_dir)
        assert len(errors) == 1
        assert errors[0]["stage"] == "compile"
        assert "not found" in errors[0]["message"].lower()
        assert errors[0]["code"] == ErrorCodes.TSC_NOT_FOUND

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_generic_compilation_error(self, mock_run_command, temp_dir):
        """Test generic TypeScript compilation error."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="",
            stderr="Some unexpected error occurred",
            returncode=1
        )

        errors = check_typescript(temp_dir)
        assert len(errors) == 1
        assert errors[0]["stage"] == "compile"
        assert "Some unexpected error" in errors[0]["message"]
        assert errors[0]["code"] == ErrorCodes.ERROR


class TestTypescriptErrorParsing:
    """Tests for TypeScript error parsing."""

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_parse_error_with_line_and_column(self, mock_run_command, temp_dir):
        """Test parsing error with line and column numbers."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout="src/main.ts(42,15): error TS2345: Argument of type 'string' is not assignable.",
            stderr="",
            returncode=1
        )

        errors = check_typescript(temp_dir)
        assert len(errors) == 1
        assert errors[0]["file"] == "src/main.ts"
        assert errors[0]["line"] == 42
        assert "Argument of type 'string'" in errors[0]["message"]

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_parse_multiple_errors_same_file(self, mock_run_command, temp_dir):
        """Test parsing multiple errors from the same file."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout=(
                "src/app.ts(10,5): error TS2304: Cannot find name 'x'.\n"
                "src/app.ts(15,8): error TS2304: Cannot find name 'y'.\n"
                "src/app.ts(20,3): error TS2304: Cannot find name 'z'."
            ),
            stderr="",
            returncode=1
        )

        errors = check_typescript(temp_dir)
        assert len(errors) == 3
        assert all(e["file"] == "src/app.ts" for e in errors)
        assert [e["line"] for e in errors] == [10, 15, 20]

    @patch('src.validators.syntactic_validators.typescript.run_command')
    def test_ignore_non_error_lines(self, mock_run_command, temp_dir):
        """Test that non-error lines are ignored."""
        mock_run_command.return_value = SubprocessResult(
            success=False,
            stdout=(
                "Compiling TypeScript files...\n"
                "src/app.ts(10,5): error TS2304: Cannot find name 'foo'.\n"
                "Found 1 error.\n"
            ),
            stderr="",
            returncode=1
        )

        errors = check_typescript(temp_dir)
        assert len(errors) == 1
        assert errors[0]["file"] == "src/app.ts"
        assert errors[0]["line"] == 10
