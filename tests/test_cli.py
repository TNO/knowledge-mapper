"""Tests for the ``knowledge-mapper`` CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge_mapper.cli import load_kb, run_kb


class _FakeKB:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def connect(self) -> None:
        self.calls.append("connect")

    async def register(self) -> None:
        self.calls.append("register")

    async def start_handling_loop(self) -> None:
        self.calls.append("start_handling_loop")

    async def unregister(self) -> None:
        self.calls.append("unregister")

    async def close(self) -> None:
        self.calls.append("close")


def _write_module(tmp_path: Path, body: str) -> Path:
    file = tmp_path / "user_app.py"
    file.write_text(body)
    return file


def test_load_kb_returns_named_attribute_from_file(tmp_path: Path):
    file = _write_module(
        tmp_path,
        "class FakeKB:\n    pass\n\nkb = FakeKB()\n",
    )

    result = load_kb(f"{file}:kb")

    assert type(result).__name__ == "FakeKB"


def test_load_kb_rejects_spec_without_colon():
    with pytest.raises(ValueError, match="path/to/file.py:attr"):
        load_kb("no_colon_here.py")


def test_load_kb_raises_when_file_missing(tmp_path: Path):
    missing = tmp_path / "no_such_file.py"

    with pytest.raises(FileNotFoundError, match=str(missing)):
        load_kb(f"{missing}:kb")


def test_load_kb_raises_when_attribute_missing(tmp_path: Path):
    file = _write_module(tmp_path, "other = 42\n")

    with pytest.raises(AttributeError, match="kb"):
        load_kb(f"{file}:kb")


async def test_run_kb_invokes_full_lifecycle_in_order():
    kb = _FakeKB()

    await run_kb(kb)

    assert kb.calls == [
        "connect",
        "register",
        "start_handling_loop",
        "unregister",
        "close",
    ]


async def test_run_kb_cleans_up_when_handling_loop_raises():
    class CrashingKB(_FakeKB):
        async def start_handling_loop(self) -> None:
            self.calls.append("start_handling_loop")
            raise RuntimeError("boom")

    kb = CrashingKB()

    with pytest.raises(RuntimeError, match="boom"):
        await run_kb(kb)

    assert kb.calls == [
        "connect",
        "register",
        "start_handling_loop",
        "unregister",
        "close",
    ]


async def test_run_kb_shuts_down_gracefully_on_sigint():
    import asyncio
    import os
    import signal

    class HangingKB(_FakeKB):
        async def start_handling_loop(self) -> None:
            self.calls.append("start_handling_loop")
            asyncio.get_running_loop().call_later(
                0.05, lambda: os.kill(os.getpid(), signal.SIGINT)
            )
            await asyncio.Event().wait()

    kb = HangingKB()
    await run_kb(kb)

    assert kb.calls == [
        "connect",
        "register",
        "start_handling_loop",
        "unregister",
        "close",
    ]


def test_run_subcommand_executes_full_lifecycle(tmp_path: Path):
    from typer.testing import CliRunner

    from knowledge_mapper.cli import app

    log = tmp_path / "calls.log"
    kb_file = _write_module(
        tmp_path,
        f"""
from pathlib import Path

LOG = Path({str(log)!r})

class FakeKB:
    async def connect(self):
        with LOG.open('a') as f: f.write('connect\\n')
    async def register(self):
        with LOG.open('a') as f: f.write('register\\n')
    async def start_handling_loop(self):
        with LOG.open('a') as f: f.write('start\\n')
    async def unregister(self):
        with LOG.open('a') as f: f.write('unregister\\n')
    async def close(self):
        with LOG.open('a') as f: f.write('close\\n')

kb = FakeKB()
""",
    )

    result = CliRunner().invoke(app, ["run", f"{kb_file}:kb"])

    assert result.exit_code == 0, result.output
    assert log.read_text().splitlines() == [
        "connect",
        "register",
        "start",
        "unregister",
        "close",
    ]


def test_load_kb_allows_sibling_imports(tmp_path: Path):
    (tmp_path / "sibling.py").write_text("MESSAGE = 'hello'\n")
    file = _write_module(
        tmp_path,
        "from sibling import MESSAGE\n\nkb = MESSAGE\n",
    )

    result = load_kb(f"{file}:kb")

    assert result == "hello"


def test_load_kb_supports_relative_imports_when_file_lives_in_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "sibling.py").write_text("MESSAGE = 'relative'\n")
    file = pkg / "main.py"
    file.write_text("from .sibling import MESSAGE\n\nkb = MESSAGE\n")

    result = load_kb(f"{file}:kb")

    assert result == "relative"


def test_load_kb_accepts_dotted_module_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pkg = tmp_path / "dotted_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "main.py").write_text("kb = 'from-dotted'\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = load_kb("dotted_pkg.main:kb")

    assert result == "from-dotted"
