"""Tests for the ``knowledge-mapper run`` CLI subcommand."""

import textwrap
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from knowledge_mapper.cli import app

runner = CliRunner()


def _write_kb_module(tmp_path: Path, *, variable: str = "kb") -> Path:
    """Write a minimal Python file that defines a KnowledgeBase."""
    module_file = tmp_path / "my_kb.py"
    module_file.write_text(
        textwrap.dedent(f"""\
            from knowledge_mapper import KnowledgeBase
            from knowledge_mapper.testing import TestClient

            {variable} = KnowledgeBase(
                id="http://example.org/cli-test#kb",
                name="cli-test-kb",
                description="A KB for CLI testing.",
                ke_url="http://fake-ke",
            )
            {variable}.client = TestClient(fake_url="http://fake-ke")
        """)
    )
    return module_file


def test_run_happy_path(tmp_path: Path):
    module_file = _write_kb_module(tmp_path)
    target = f"{module_file}:kb"

    with patch("knowledge_mapper.kb.knowledge_base.KnowledgeBase.start_handling_loop"):
        result = runner.invoke(app, ["run", target])

    assert result.exit_code == 0


def test_run_invalid_target_format():
    result = runner.invoke(app, ["run", "no_colon_here"])

    assert result.exit_code != 0
    assert "Invalid target" in (result.output + result.stderr)


def test_run_file_not_found():
    result = runner.invoke(app, ["run", "nonexistent_file.py:kb"])

    assert result.exit_code != 0
    assert "File not found" in (result.output + result.stderr)


def test_run_attribute_not_found(tmp_path: Path):
    module_file = _write_kb_module(tmp_path)
    target = f"{module_file}:nonexistent"

    result = runner.invoke(app, ["run", target])

    assert result.exit_code != 0
    assert "no attribute 'nonexistent'" in (result.output + result.stderr)


def test_run_wrong_type(tmp_path: Path):
    module_file = tmp_path / "wrong_type.py"
    module_file.write_text("kb = 'not a KnowledgeBase'\n")
    target = f"{module_file}:kb"

    result = runner.invoke(app, ["run", target])

    assert result.exit_code != 0
    assert "not a KnowledgeBase instance" in (result.output + result.stderr)


def test_run_module_with_syntax_error(tmp_path: Path):
    module_file = tmp_path / "bad_syntax.py"
    module_file.write_text("def broken(\n")
    target = f"{module_file}:kb"

    result = runner.invoke(app, ["run", target])

    assert result.exit_code != 0
    assert "Error executing" in (result.output + result.stderr)
