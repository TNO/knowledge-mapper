from typing import Self

from ..ke.models import KiTypes
from ..knowledge_interaction import Handler, KnowledgeInteractionContext
from ..settings import KnowledgeBaseSettings
from .knowledge_base import KnowledgeBase


class KnowledgeBaseBuilder:
    """Builds a :class:`KnowledgeBase` from a :class:`~.settings.KnowledgeBaseSettings`
    instance.

    Returned by :meth:`KnowledgeBase.from_settings`. Attach handlers for incoming
    (ANSWER/REACT) knowledge interactions via :meth:`handler`, then call :meth:`build`
    to obtain the configured :class:`KnowledgeBase`. ASK and POST KIs defined in
    settings are registered automatically — no explicit call needed.

    Example::

        builder = KnowledgeBase.from_settings(settings)

        @builder.handler("my-answer-ki")
        def my_handler(binding_set, info):
            return binding_set

        kb = builder.build()
        kb.connect()
        kb.register()
        kb.start_handling_loop()
    """

    def __init__(self, settings: KnowledgeBaseSettings) -> None:
        self._settings = settings
        self._kb = KnowledgeBase(
            id=settings.knowledge_base.id,
            name=settings.knowledge_base.name,
            description=settings.knowledge_base.description,
            ke_url=settings.knowledge_engine_endpoint,
            lease_renewal_time=settings.knowledge_base.lease_renewal_time,
            reasoner_level=settings.knowledge_base.reasoner_level,
        )
        self._unhandled_incoming: set[str] = {
            ki.name
            for ki in settings.knowledge_interactions
            if ki.type in (KiTypes.ANSWER, KiTypes.REACT)
        }

    def handler(self, ki_name: str, func: Handler) -> Self:
        """Attach *func* as the handler for the ANSWER or REACT KI named *ki_name*.

        Args:
            ki_name: Name of the KI as declared in settings.
            func: Handler callable; receives a binding set and
                :class:`~.ke.models.KnowledgeInteractionInfo` and returns a binding set.

        Raises:
            ValueError: If *ki_name* is not declared in settings, or if the KI is of
                type ASK or POST (outgoing KIs do not take handlers; they are registered
                automatically).
        """
        try:
            info = self._settings.get_configured_interaction(ki_name)
        except ValueError as err:
            raise ValueError(f"KI named '{ki_name}' not found in settings.") from err

        if info.type not in (KiTypes.ANSWER, KiTypes.REACT):
            raise ValueError(
                f"KI '{ki_name}' is of type {info.type}. Only ANSWER and REACT KIs "
                f"accept a handler; ASK and POST KIs are registered automatically."
            )

        self._kb._register_ki_decorator(info=info, defer_ke_registration=True)(func)
        self._unhandled_incoming.discard(ki_name)
        return self

    def build(self) -> KnowledgeBase:
        """Return the configured :class:`KnowledgeBase`.

        All ASK and POST KIs from settings are registered at this point. ANSWER and
        REACT KIs must have had their handlers attached via :meth:`handler` before
        calling ``build()``.

        Raises:
            ValueError: If any ANSWER or REACT KI from settings has no handler.
        """
        if self._unhandled_incoming:
            names = ", ".join(sorted(self._unhandled_incoming))
            raise ValueError(
                f"The following ANSWER/REACT KIs from settings have no handler "
                f"attached: {names}. Call builder.handler(ki_name, func) for each "
                f"before building."
            )

        for ki in self._settings.knowledge_interactions:
            if ki.type in (KiTypes.ASK, KiTypes.POST):
                self._kb._register_ki_locally(
                    KnowledgeInteractionContext(
                        info=ki,
                        handler=None,
                    ),
                )

        return self._kb
