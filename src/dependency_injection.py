"""Dependency injection resolver for KI handler parameters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, get_args, get_type_hints


@dataclass
class Depends:
    """Mark a handler parameter as a resolved dependency.

    Usage::

        def get_db() -> MyDatabase:
            return MyDatabase(url="...")

        @kb.answer_ki(name="...", graph_pattern="...")
        def handler(
            binding_set: list[PersonBinding],
            info: KnowledgeInteractionInfo,
            db: Annotated[MyDatabase, Depends(get_db)],
        ) -> list[PersonBinding]:
            return db.query(binding_set)

    Args:
        factory: A callable (sync) that returns the dependency value.  The
            factory may itself declare ``Annotated[T, Depends(...)]`` parameters
            for nested/transitive resolution.
        cache: When ``True`` (the default) the factory is called at most once
            per KI-call invocation and the result is shared across all
            parameters that reference the same factory.  When ``False`` the
            factory is called fresh every time it is needed.
    """

    factory: Callable[..., Any]
    cache: bool = field(default=True)


def _get_dep_params(func: Callable[..., Any]) -> dict[str, Depends]:
    """Return a mapping of parameter-name → Depends for all Annotated Depends params."""
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception:
        return {}

    dep_params: dict[str, Depends] = {}
    for name, hint in hints.items():
        if name == "return":
            continue
        if not hasattr(hint, "__metadata__"):
            continue
        for meta in get_args(hint)[1:]:
            if isinstance(meta, Depends):
                dep_params[name] = meta
                break
    return dep_params


def resolve_dependencies(
    func: Callable[..., Any],
    cache: dict[Callable[..., Any], Any] | None = None,
) -> dict[str, Any]:
    """Resolve all ``Annotated[T, Depends(...)]`` parameters of *func*.

    Args:
        func: The callable whose parameters should be inspected.
        cache: A per-call cache mapping factory → resolved value.  Pass the
            same dict for all calls within a single KI invocation so that
            ``cache=True`` factories are called at most once.  Pass ``None``
            to start fresh (a new empty dict will be created).

    Returns:
        A dict mapping parameter name → resolved value for every
        ``Depends``-annotated parameter found in *func*'s signature.
    """
    if cache is None:
        cache = {}

    dep_params = _get_dep_params(func)
    resolved: dict[str, Any] = {}
    for param_name, dep in dep_params.items():
        factory = dep.factory
        if dep.cache and factory in cache:
            resolved[param_name] = cache[factory]
        else:
            # Recursively resolve factory's own dependencies first
            factory_kwargs = resolve_dependencies(factory, cache)
            value = factory(**factory_kwargs)
            if dep.cache:
                cache[factory] = value
            resolved[param_name] = value
    return resolved
