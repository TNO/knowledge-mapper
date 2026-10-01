"""Dependency injection resolver for KI handler parameters."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, get_args, get_type_hints

from .ke.models import KnowledgeBaseId

REQUESTING_KB_ID_PARAM = "requesting_kb_id"


@dataclass
class Depends:
    """Mark a handler parameter as a resolved dependency.

    Usage::

        def get_db() -> MyDatabase:
            return MyDatabase(url="...")

        @kb.answer_ki(name="...", graph_pattern="...")
        def handler(
            binding_set: list[PersonBinding],
            info: KnowledgeInteraction,
            db: Annotated[MyDatabase, Depends(get_db)],
        ) -> list[PersonBinding]:
            return db.query(binding_set)

    Args:
        factory: A callable (sync or async) that returns the dependency
            value.  The factory may itself declare
            ``Annotated[T, Depends(...)]`` parameters for nested/transitive
            resolution.
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


def _get_provided_params(
    func: Callable[..., Any],
    provided: Mapping[str, Any],
    dep_params: Mapping[str, Depends],
) -> dict[str, Any]:
    """Return the *provided* values whose name matches a non-Depends param of *func*."""
    if not provided:
        return {}
    try:
        param_names = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return {}
    return {
        name: provided[name]
        for name in param_names
        if name in provided and name not in dep_params
    }


def get_requesting_kb_id(requesting_kb_id: KnowledgeBaseId) -> KnowledgeBaseId:
    """Dependency factory returning the ID of the KB that initiated the KI call.

    Usage::

        @kb.answer_ki(name="...", graph_pattern="...")
        def handler(
            binding_set: BindingSet,
            info: KnowledgeInteraction,
            caller: Annotated[KnowledgeBaseId, Depends(get_requesting_kb_id)],
        ) -> BindingSet: ...

    Handlers and dependency factories can also declare a parameter named
    ``requesting_kb_id`` directly to receive the same value.
    """
    return requesting_kb_id


async def resolve_dependencies(
    func: Callable[..., Any],
    cache: dict[Callable[..., Any], Any] | None = None,
    overrides: dict[Callable[..., Any], Callable[..., Any]] | None = None,
    provided: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the injectable parameters of *func*.

    Injectable parameters are ``Annotated[T, Depends(...)]`` parameters and
    parameters whose name is a key of *provided*.

    Args:
        func: The callable whose parameters should be inspected.
        cache: A per-call cache mapping factory → resolved value.  Pass the
            same dict for all calls within a single KI invocation so that
            ``cache=True`` factories are called at most once.  Pass ``None``
            to start fresh (a new empty dict will be created).
        overrides: An optional mapping of original factory → replacement
            factory.  When a ``Depends`` factory appears as a key in this
            dict, the corresponding override callable is invoked instead.
            Overrides are checked transitively at every level of the
            dependency tree.
        provided: Per-call values injected by parameter name into *func*
            and, transitively, into every dependency factory (e.g.
            ``requesting_kb_id``).  A ``Depends`` annotation on a parameter
            takes precedence over a provided value of the same name.

    Returns:
        A dict mapping parameter name → resolved value for every injectable
        parameter found in *func*'s signature.
    """
    if cache is None:
        cache = {}
    if provided is None:
        provided = {}

    dep_params = _get_dep_params(func)
    resolved: dict[str, Any] = _get_provided_params(func, provided, dep_params)
    for param_name, dep in dep_params.items():
        factory = dep.factory
        actual_factory = (
            overrides[factory] if overrides and factory in overrides else factory
        )
        if dep.cache and actual_factory in cache:
            resolved[param_name] = cache[actual_factory]
        else:
            factory_kwargs = await resolve_dependencies(
                actual_factory, cache, overrides, provided
            )
            if inspect.iscoroutinefunction(actual_factory):
                value = await actual_factory(**factory_kwargs)
            else:
                value = actual_factory(**factory_kwargs)
            if dep.cache:
                cache[actual_factory] = value
            resolved[param_name] = value
    return resolved
