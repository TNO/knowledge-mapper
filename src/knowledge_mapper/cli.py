"""CLI for the Knowledge Mapper. See ``knowledge-mapper --help``."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import importlib.util
import signal
import sys
from pathlib import Path
from types import ModuleType
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
    """Load a knowledge base instance from a ``target:attr`` spec.

    ``target`` may be either:

    * A filesystem path to a ``.py`` file (e.g. ``path/to/file.py``). The
      file's parent directory is added to ``sys.path`` so it can import
      sibling modules. If the file lives inside a package (its directory
      contains ``__init__.py``), the file is imported under its fully
      qualified package name so relative imports resolve.
    * A dotted module path (e.g. ``my_pkg.main``). The module is imported
      via the normal import machinery and must be installed or otherwise
      reachable on ``sys.path``.
    """
    if ":" not in spec:
        raise ValueError(
            f"Invalid spec {spec!r}: expected 'path/to/file.py:attr' "
            "or 'pkg.module:attr'."
        )
    target, attr = spec.rsplit(":", 1)

    if _looks_like_path(target):
        module = _import_from_path(target)
    else:
        module = importlib.import_module(target)

    return getattr(module, attr)


def _looks_like_path(target: str) -> bool:
    return target.endswith(".py") or "/" in target or "\\" in target


def _import_from_path(path_str: str) -> ModuleType:
    file = Path(path_str).resolve()
    if not file.is_file():
        raise FileNotFoundError(str(file))

    pkg_parts: list[str] = []
    parent = file.parent
    while (parent / "__init__.py").is_file():
        pkg_parts.insert(0, parent.name)
        parent = parent.parent

    sys_path_entry = str(parent)
    if sys_path_entry not in sys.path:
        sys.path.insert(0, sys_path_entry)

    if pkg_parts:
        qualified = ".".join([*pkg_parts, file.stem])
        return importlib.import_module(qualified)

    module_spec = importlib.util.spec_from_file_location(file.stem, file)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[file.stem] = module
    module_spec.loader.exec_module(module)
    return module


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
