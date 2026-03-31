import logging
from collections.abc import Callable
from enum import StrEnum
from functools import wraps

from .ke import Client
from .ke.client import PollResult
from .ke.errors import KnowledgeEngineNotAvailableError
from .ke.models import (
    AskAnswerInteractionInfo,
    BindingSet,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
)
from .knowledge_interaction import (
    Handler,
    KnowledgeInteractionContext,
    KnowledgeInteractionStatus,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseState(StrEnum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"


class KnowledgeBase:
    """This knowledge base is used for registering and unregistering at a Knowledge
    Engine runtime, registering knowledge interactions and calling its handlers.
    Starts in unregistered state.
    """

    def __init__(self, id: str, name: str, description: str, ke_url: str):
        self.state = KnowledgeBaseState.UNREGISTERED
        self.ki_registry: dict[str, KnowledgeInteractionContext] = {}
        self.client = Client(ke_url)
        self.info = KnowledgeBaseInfo(
            id=id,
            name=name,
            description=description,
        )

    def connect(self) -> None:
        """Checks whether the KE runtime is available and raises an exception if not.

        Raises:
            KnowledgeEngineNotAvailableError: If the KE runtime cannot be reached.
        """
        if not self.client.ke_is_available():
            raise KnowledgeEngineNotAvailableError(self.client.ke_url)

    def register(self) -> None:
        """Register this knowledge base at the KE runtime, reregister if already
        registered. Automatically syncs knowledge interactions with KE runtime.

        Raises:
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        logger.info(
            "Registering knowledge base '%s' (%s).", self.info.id, self.info.name
        )
        self.client.register_kb(self.info, reregister=True)
        self.state = KnowledgeBaseState.REGISTERED
        self.sync_knowledge_interactions()
        return

    def unregister(self) -> None:
        """Unregister this knowledge base at the KE runtime, do nothing if not currently
        registered. Knowledge interactions automatically unregistered.

        Raises:
            SmartConnectorNotFoundError: If the KB's smart connector is not found in the
              KE runtime.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
              response.
        """
        if self.state != KnowledgeBaseState.REGISTERED:
            logger.warning(
                "Knowledge base '%s' (%s) is not registered, cannot unregister.",
                self.info.id,
                self.info.name,
            )
            return

        logger.info(
            "Unregistering knowledge base '%s' (%s).", self.info.id, self.info.name
        )
        self.client.unregister_kb(self.info.id)
        self.state = KnowledgeBaseState.UNREGISTERED
        for ki_ctx in self.ki_registry.values():
            ki_ctx.status = KnowledgeInteractionStatus.UNREGISTERED
        return

    def register_ki(
        self, ki_ctx: KnowledgeInteractionContext, defer_ke_registration: bool = False
    ) -> KnowledgeInteractionInfo:
        """Register a knowledge interaction for this knowledge base at the KE runtime
        and store it in this object's registry of interactions.

        Raises:
            ValueError: If the KB is not yet registered and ``defer_ke_registration`` is
                ``False``, if a KI with the same name is already registered, or if the
                given KI context is already in a registered state.
            SmartConnectorNotFoundError: If the KB's smart connector is not found in the
                KE runtime (only when ``defer_ke_registration`` is ``False``).
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
                response (only when ``defer_ke_registration`` is ``False``).
        """
        if self.state != KnowledgeBaseState.REGISTERED and not defer_ke_registration:
            raise ValueError(
                f"Cannot register KI '{ki_ctx.info.name}' because the KB is not "
                f"registered. Consider setting defer_ke_registration=True to defer "
                f"registration until the KB itself is registered."
            )
        if ki_ctx.info.name in (ki.info.name for ki in self.ki_registry.values()):
            raise ValueError(
                f"A KI named '{ki_ctx.info.name}' is already registered for this KB."
            )
        if ki_ctx.status == KnowledgeInteractionStatus.REGISTERED:
            raise ValueError(
                f"Cannot register KI '{ki_ctx.info.name}' because it is already "
                f"registered."
            )

        self.ki_registry[ki_ctx.info.name] = ki_ctx
        if defer_ke_registration:
            return ki_ctx.info

        registered_ki = self.client.register_ki(
            kb_id=self.info.id,
            ki=ki_ctx.info,
        )
        ki_ctx.info = registered_ki
        ki_ctx.status = KnowledgeInteractionStatus.REGISTERED
        return registered_ki

    def _register_ki_decorator(
        self, info: KnowledgeInteractionInfo, defer_ke_registration: bool
    ) -> Callable[[Handler], Handler]:
        """Return a decorator that registers the decorated function as a KI handler.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
              violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """

        def decorator(func: Handler) -> Handler:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.register_ki(
                KnowledgeInteractionContext(
                    info=info,
                    handler=func,
                    status=KnowledgeInteractionStatus.UNREGISTERED,
                ),
                defer_ke_registration=defer_ke_registration,
            )
            return wrapper

        return decorator

    def sync_knowledge_interactions(self) -> None:
        """Synchronize registration of knowledge interactions in this object's registry
        with the interactions registered at the KE runtime, so all unregistered KIs in
        the registry are registered.

        Raises:
            ValueError: If the KB is not registered.
            SmartConnectorNotFoundError: If the KB's smart connector is not found in
            the KE runtime.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        if self.state != KnowledgeBaseState.REGISTERED:
            raise ValueError(
                "Cannot sync KIs because the KB is not registered. Please register "
                "the KB first."
            )
        for ki_ctx in self.ki_registry.values():
            if ki_ctx.status == KnowledgeInteractionStatus.REGISTERED:
                continue
            ki_ctx.info = self.client.register_ki(
                kb_id=self.info.id,
                ki=ki_ctx.info,
            )
            ki_ctx.status = KnowledgeInteractionStatus.REGISTERED
        return

    def ask_ki(
        self,
        name: str,
        graph_pattern: str,
        prefixes: dict = None,
        defer_ke_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        """Return a decorator that registers the decorated function as an ASK KI
        handler.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
            violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        return self._register_ki_decorator(
            info=AskAnswerInteractionInfo(
                type=KiTypes.ASK,
                name=name,
                prefixes=prefixes or dict(),
                graph_pattern=graph_pattern,
            ),
            defer_ke_registration=defer_ke_registration,
        )

    def answer_ki(
        self,
        name: str,
        graph_pattern: str,
        prefixes: dict = None,
        defer_ke_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        """Return a decorator that registers the decorated function as an ANSWER KI
        handler.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
            violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        return self._register_ki_decorator(
            info=AskAnswerInteractionInfo(
                type=KiTypes.ANSWER,
                name=name,
                prefixes=prefixes or dict(),
                graph_pattern=graph_pattern,
            ),
            defer_ke_registration=defer_ke_registration,
        )

    def post_ki(
        self,
        name: str,
        argument_graph_pattern: str,
        result_graph_pattern: str,
        prefixes: dict = None,
        defer_ke_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        """Return a decorator that registers the decorated function as a POST KI
        handler.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
            violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        return self._register_ki_decorator(
            info=PostReactInteractionInfo(
                type=KiTypes.POST,
                name=name,
                prefixes=prefixes or dict(),
                argument_graph_pattern=argument_graph_pattern,
                result_graph_pattern=result_graph_pattern,
            ),
            defer_ke_registration=defer_ke_registration,
        )

    def react_ki(
        self,
        name: str,
        argument_graph_pattern: str,
        result_graph_pattern: str,
        prefixes: dict = None,
        defer_ke_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        """Return a decorator that registers the decorated function as a REACT KI
        handler.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
            violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        return self._register_ki_decorator(
            info=PostReactInteractionInfo(
                type=KiTypes.REACT,
                name=name,
                prefixes=prefixes or dict(),
                argument_graph_pattern=argument_graph_pattern,
                result_graph_pattern=result_graph_pattern,
            ),
            defer_ke_registration=defer_ke_registration,
        )

    def call(self, binding_set: BindingSet, ki_id: str) -> BindingSet:
        """Invoke the handler of a registered KI by its ID.

        Raises:
            KeyError: If ``ki_id`` is not found in the local KI registry.
        """
        ki_ctx = self.ki_registry[ki_id]
        result = ki_ctx.handler(binding_set)
        return result

    def start_handling_loop(self, loops: int = None) -> None:
        """Poll the KE runtime for incoming KI calls and dispatch them to handlers.

        Runs until an EXIT signal is received from the KE runtime, or until
        ``loops`` iterations have been completed if ``loops`` is specified.

        Raises:
            RuntimeError: If the KB is not registered.
            KeyError: If the KE runtime refers to a KI not found in the local registry.
            SmartConnectorNotFoundError: If the KB's smart connector is not found in
            the KE runtime.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
            Exception: If an unexpected poll result is returned.
        """
        if self.state != KnowledgeBaseState.REGISTERED:
            raise RuntimeError(
                "Cannot start handling loop because the KB is not registered. Please "
                "register the KB first."
            )

        loops_done = 0
        while loops is None or loops_done < loops:
            loops_done += 1
            poll_result, maybe_handle_request = self.client.poll_ki_call(
                kb_id=self.info.id
            )
            match poll_result, maybe_handle_request:
                case PollResult.HANDLE, _:
                    self.call(
                        maybe_handle_request.binding_set,
                        maybe_handle_request.knowledge_interaction_id,
                    )
                case PollResult.REPOLL, None:
                    continue
                case PollResult.EXIT, None:
                    logger.info("Received exit signal from KE, stopping handling loop.")
                    return
                case _:
                    raise Exception(
                        f"Unexpected poll result: {poll_result} or request:"
                        f"{maybe_handle_request}"
                    )

    @property
    def is_registered(self) -> bool:
        """Is the knowledge base in the registered state"""
        return self.state == KnowledgeBaseState.REGISTERED
