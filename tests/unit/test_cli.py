"""Tests for CLI entry point."""

import argparse
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.cli import build_parser, cmd_generate, cmd_generate_mixed, cmd_generate_raw, main


class TestBuildParser:
    """Tests for build_parser function."""

    def test_returns_argument_parser(self):
        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_has_three_subcommands(self):
        parser = build_parser()
        subactions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        assert len(subactions) == 1
        choices = subactions[0].choices
        assert {"compile", "validate", "generate-file", "experiments"}.issubset(choices.keys())

    def test_dsl_subparser_arguments(self):
        parser = build_parser()
        dsl_parser = parser._subparsers._group_actions[0].choices["dsl"]
        dsl_args = {a.dest: a for a in dsl_parser._actions}
        assert dsl_args["description"].required is True
        assert dsl_args["blueprint"].default == "./blueprint.yaml"
        assert dsl_args["project"].default == "./nest_project"

    def test_raw_subparser_arguments(self):
        parser = build_parser()
        raw_parser = parser._subparsers._group_actions[0].choices["raw"]
        raw_args = {a.dest: a for a in raw_parser._actions}
        assert raw_args["description"].required is True
        assert raw_args["project"].default == "./nest_project"
        assert "blueprint" not in raw_args

    def test_mixed_subparser_arguments(self):
        parser = build_parser()
        mixed_parser = parser._subparsers._group_actions[0].choices["mixed"]
        mixed_args = {a.dest: a for a in mixed_parser._actions}
        assert mixed_args["description"].required is True
        assert mixed_args["blueprint"].default == "./mixed_blueprint.yaml"
        assert mixed_args["project"].default == "./nest_project"

    def test_global_model_argument(self):
        parser = build_parser()
        args = {a.dest: a for a in parser._actions}
        assert "model" in args
        assert args["model"].default is None


class TestCmdGenerate:
    """Tests for cmd_generate function (DSL pipeline)."""

    def test_success(self):
        args = MagicMock(description="test app", blueprint="bp.yaml", project="./out", model="gemini")
        result = SimpleNamespace(
            content="yaml_content",
            provider="gemini",
            duration_seconds=1.0,
            total_tokens=10,
            input_tokens=5,
            output_tokens=5,
        )
        with (
            patch("apps.cli.main.natural_language_to_yaml") as mock_nl,
            patch("apps.cli.main.save_blueprint") as mock_save,
            patch("apps.cli.main.dsl_generate_main") as mock_gen,
            patch("apps.cli.main.log_generation_statistics"),
            patch("apps.cli.main.logger"),
        ):
            mock_nl.return_value = result
            cmd_generate(args)

        mock_nl.assert_called_once_with("test app", provider="gemini")
        mock_save.assert_called_once_with("yaml_content", "bp.yaml")
        mock_gen.assert_called_once_with("bp.yaml", "./out")

    def test_generation_failure_exits(self):
        args = MagicMock(description="test", blueprint="bp.yaml", project="./out", model="gemini")
        result = SimpleNamespace(
            content="yaml",
            provider="gemini",
            duration_seconds=1.0,
            total_tokens=10,
            input_tokens=5,
            output_tokens=5,
        )
        with (
            patch("apps.cli.main.natural_language_to_yaml") as mock_nl,
            patch("apps.cli.main.save_blueprint"),
            patch("apps.cli.main.dsl_generate_main", side_effect=Exception("fail")),
            patch("apps.cli.main.logger"),
        ):
            mock_nl.return_value = result
            with pytest.raises(SystemExit) as exc:
                cmd_generate(args)
        assert exc.value.code == 1


class TestCmdGenerateRaw:
    """Tests for cmd_generate_raw function."""

    def test_success(self):
        args = MagicMock(description="test", project="./out", model="groq")
        gen_result = SimpleNamespace(
            content="code",
            provider="groq",
            duration_seconds=0.5,
            total_tokens=5,
            input_tokens=2,
            output_tokens=3,
        )
        with (
            patch("packages.llm_providers.generators.raw_generate.generate_code_files") as mock_gen,
            patch("packages.llm_providers.generators.raw_generate.save_files") as mock_save,
            patch("apps.cli.main.log_generation_statistics"),
            patch("apps.cli.main.logger"),
        ):
            mock_gen.return_value = (gen_result, {"file.ts": "content"})
            cmd_generate_raw(args)

        mock_gen.assert_called_once_with("test", "./out", provider="groq")
        mock_save.assert_called_once_with({"file.ts": "content"}, "./out")


class TestCmdGenerateMixed:
    """Tests for cmd_generate_mixed function."""

    def test_success(self):
        args = MagicMock(description="test", blueprint="bp.yaml", project="./out", model="openrouter")
        with (
            patch("packages.llm_providers.generators.mixed_generate.mixed_generate") as mock_mixed,
            patch("packages.llm_providers.generators.mixed_generate.save_mixed_files") as mock_save,
            patch("apps.cli.main.logger"),
        ):
            mock_mixed.return_value = {"success": True, "files": {"f.ts": "c"}}
            cmd_generate_mixed(args)

        mock_mixed.assert_called_once_with(
            description="test",
            output_dir="./out",
            blueprint_path="bp.yaml",
            primary_model="openrouter",
        )
        mock_save.assert_called_once_with({"f.ts": "c"}, "./out")

    def test_failure_exits(self):
        args = MagicMock(description="test", blueprint="bp.yaml", project="./out", model="openrouter")
        with (
            patch("packages.llm_providers.generators.mixed_generate.mixed_generate") as mock_mixed,
            patch("apps.cli.main.logger"),
        ):
            mock_mixed.return_value = {"success": False, "error": "something went wrong"}
            with pytest.raises(SystemExit) as exc:
                cmd_generate_mixed(args)
        assert exc.value.code == 1


class TestMain:
    """Tests for main entry point dispatch."""

    def test_dispatch_dsl(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "dsl", "my app"])
        with (
            patch("apps.cli.main.cmd_generate") as mock_cmd,
            patch("apps.cli.main.build_parser", wraps=build_parser),
        ):
            main()
        mock_cmd.assert_called_once()

    def test_dispatch_raw(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "raw", "my app"])
        with (
            patch("apps.cli.main.cmd_generate_raw") as mock_cmd,
            patch("apps.cli.main.build_parser", wraps=build_parser),
        ):
            main()
        mock_cmd.assert_called_once()

    def test_dispatch_mixed(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "mixed", "my app"])
        with (
            patch("apps.cli.main.cmd_generate_mixed") as mock_cmd,
            patch("apps.cli.main.build_parser", wraps=build_parser),
        ):
            main()
        mock_cmd.assert_called_once()
