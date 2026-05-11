from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


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
