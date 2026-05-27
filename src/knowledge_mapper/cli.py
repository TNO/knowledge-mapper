"""CLI entry point for the knowledge-mapper package.

Provides the ``knowledge-mapper`` console command with subcommands for running
a Python-defined KnowledgeBase.
"""

from __future__ import annotations

import importlib.util
import logging
import signal
import sys
from pathlib import Path
from types import FrameType

import typer

from .kb.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="knowledge-mapper",
    help="CLI for the knowledge-mapper SDK.",
    add_completion=False,
)


@app.callback()
def _main() -> None:
    """CLI for the knowledge-mapper SDK."""


def _fail(message: str) -> None:
    """Print an error message and exit with code 1."""
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def _load_kb(target: str) -> KnowledgeBase:
    """Load a KnowledgeBase instance from a ``path:attribute`` target string."""
    if ":" not in target:
        _fail(
            f"Invalid target '{target}'. Expected format: 'path/to/module.py:variable'."
        )

    file_path_str, attr_name = target.rsplit(":", 1)
    file_path = Path(file_path_str)

    if not file_path.is_file():
        _fail(f"File not found: '{file_path}'.")

    spec = importlib.util.spec_from_file_location("_km_user_module", file_path)
    if spec is None or spec.loader is None:
        _fail(f"Could not load module from '{file_path}'.")  # pragma: no cover

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        _fail(f"Error executing '{file_path}': {exc}")

    if not hasattr(module, attr_name):
        _fail(f"Module '{file_path}' has no attribute '{attr_name}'.")

    kb = getattr(module, attr_name)
    if not isinstance(kb, KnowledgeBase):
        _fail(
            f"'{attr_name}' in '{file_path}' is not a KnowledgeBase instance "
            f"(got {type(kb).__name__})."
        )

    return kb  # type: ignore[return-value]


@app.command()
def run(
    target: str = typer.Argument(
        help=(
            "Python file and KnowledgeBase variable to run, "
            "in 'path/to/module.py:variable' format."
        ),
    ),
) -> None:
    """Load a KnowledgeBase from a Python file and run its lifecycle.

    Registers the KB, enters the handling loop, and unregisters on
    SIGINT/SIGTERM.
    """
    kb = _load_kb(target)

    def _shutdown(signum: int, frame: FrameType | None) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down.", sig_name)
        kb.unregister()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    kb.register()
    logger.info(
        "Knowledge base '%s' registered. Entering handling loop.",
        kb.info.name,
    )

    try:
        kb.start_handling_loop()
    finally:
        kb.unregister()
