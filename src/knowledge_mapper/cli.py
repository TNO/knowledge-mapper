"""CLI for the Knowledge Mapper. See ``knowledge-mapper --help``."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import signal
import sys
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(
    help="Knowledge Mapper CLI.",
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    """Knowledge Mapper CLI."""


def load_kb(spec: str) -> Any:
    """Load a knowledge base instance from a ``path/to/file.py:attr`` spec.

    The file's parent directory is added to ``sys.path`` so the loaded module
    can import sibling modules just like when run directly with ``python``.
    """
    if ":" not in spec:
        raise ValueError(
            f"Invalid spec {spec!r}: expected 'path/to/file.py:attr'."
        )
    path_part, attr = spec.split(":", 1)
    file = Path(path_part).resolve()

    parent = str(file.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    module_spec = importlib.util.spec_from_file_location(file.stem, file)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return getattr(module, attr)


_SHUTDOWN_SIGNALS = (signal.SIGINT, signal.SIGTERM)


async def run_kb(kb: Any) -> None:
    """Run the full lifecycle of a knowledge base.

    Connects, registers, and starts the handling loop. On SIGINT/SIGTERM the
    loop is cancelled and the KB is unregistered and closed before returning.
    """
    await kb.connect()
    await kb.register()

    loop = asyncio.get_running_loop()
    handling_task = asyncio.create_task(kb.start_handling_loop())

    def _request_shutdown() -> None:
        handling_task.cancel()

    installed: list[int] = []
    for sig in _SHUTDOWN_SIGNALS:
        try:
            loop.add_signal_handler(sig, _request_shutdown)
            installed.append(sig)
        except NotImplementedError:
            pass

    try:
        with contextlib.suppress(asyncio.CancelledError):
            await handling_task
    finally:
        for sig in installed:
            loop.remove_signal_handler(sig)
        await kb.unregister()
        await kb.close()


@app.command("run")
def run_command(
    spec: str = typer.Argument(
        ...,
        metavar="PATH:ATTR",
        help="Python file and attribute, e.g. 'my_app.py:kb'.",
    ),
) -> None:
    """Run a KnowledgeBase defined in a Python file."""
    kb = load_kb(spec)
    asyncio.run(run_kb(kb))


