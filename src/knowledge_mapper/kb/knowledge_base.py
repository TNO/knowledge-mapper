from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any

from ..dependency_injection import resolve_dependencies
from ..ke import Client
from ..ke.client import ClientProtocol, PollResult
from ..ke.errors import KnowledgeEngineNotAvailableError
from ..ke.models import (
    AskAnswerInteractionInfo,
    BindingModel,
    BindingSet,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
)
from ..knowledge_interaction import (
    Handler,
    KnowledgeInteractionContext,
    KnowledgeInteractionStatus,
)

if TYPE_CHECKING:
    from ..settings import KnowledgeBaseSettings
    from .builder import KnowledgeBaseBuilder

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
        self.ki_registry: dict[str, KnowledgeInteractionContext[Any, ...]] = {}
        self.client: ClientProtocol = Client(ke_url)
        self.info = KnowledgeBaseInfo(
            id=id,
            name=name,
            description=description,
        )

    @classmethod
    def from_settings(cls, settings: KnowledgeBaseSettings) -> KnowledgeBaseBuilder:
        """Create a :class:`~.knowledge_base_builder.KnowledgeBaseBuilder` from a
        :class:`~.settings.KnowledgeBaseSettings` instance (or a subclass thereof).

        Attach handlers for incoming KIs via the builder's
        :meth:`~.knowledge_base_builder.KnowledgeBaseBuilder.handler` method, then call
        :meth:`~.knowledge_base_builder.KnowledgeBaseBuilder.build` to obtain the
        configured :class:`KnowledgeBase`.
        """
        from .builder import KnowledgeBaseBuilder

        return KnowledgeBaseBuilder(settings)

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
        self,
        ki_ctx: KnowledgeInteractionContext[Any, ...],
        defer_ke_registration: bool = False,
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
            def wrapper(
                binding_set: BindingSet | list[BindingModel],
                info: KnowledgeInteractionInfo,
                *args,
                **kwargs,
            ) -> BindingSet | Sequence[BindingModel]:
                return func(binding_set, info, *args, **kwargs)

            self.register_ki(
                KnowledgeInteractionContext(
                    info=info,
                    handler=wrapper,
                    status=KnowledgeInteractionStatus.UNREGISTERED,
                ),
                defer_ke_registration=defer_ke_registration,
            )
            return wrapper

        return decorator

    def sync_knowledge_interactions(self) -> None:
        """Synchronize registration of knowledge interactions in this object's local
        KI registry with the interactions registered at the KE runtime, so all
        unregistered KIs in the local registry are registered.

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

    def ki_from_info(
        self,
        info: KnowledgeInteractionInfo,
        defer_ke_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        """Return a decorator that registers the decorated function as a KI handler
        based on the provided KnowledgeInteractionInfo.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
              violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        return self._register_ki_decorator(
            info=info, defer_ke_registration=defer_ke_registration
        )

    def ask_ki(
        self,
        name: str,
        graph_pattern: str,
        binding_model: type[BindingModel] | None = None,
        prefixes: dict | None = None,
        defer_ke_registration: bool = True,
    ) -> None:
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
        self.register_ki(
            KnowledgeInteractionContext(
                info=AskAnswerInteractionInfo(
                    type=KiTypes.ASK,
                    name=name,
                    prefixes=prefixes or dict(),
                    graph_pattern=graph_pattern,
                ),
                handler=None,
                status=KnowledgeInteractionStatus.UNREGISTERED,
                validation_model=binding_model,
                serialization_model=binding_model,
            ),
            defer_ke_registration=defer_ke_registration,
        )
        return

    def answer_ki(
        self,
        name: str,
        graph_pattern: str,
        prefixes: dict | None = None,
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
        argument_binding_model: type[BindingModel] | None = None,
        result_binding_model: type[BindingModel] | None = None,
        prefixes: dict | None = None,
        defer_ke_registration: bool = True,
    ) -> None:
        """Register a POST KI at the KE runtime with optional argument and result
        binding models.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
            violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        self.register_ki(
            KnowledgeInteractionContext(
                info=PostReactInteractionInfo(
                    type=KiTypes.POST,
                    name=name,
                    prefixes=prefixes or dict(),
                    argument_graph_pattern=argument_graph_pattern,
                    result_graph_pattern=result_graph_pattern,
                ),
                handler=None,
                status=KnowledgeInteractionStatus.UNREGISTERED,
                validation_model=result_binding_model,
                serialization_model=argument_binding_model,
            ),
            defer_ke_registration=defer_ke_registration,
        )
        return

    def react_ki(
        self,
        name: str,
        argument_graph_pattern: str,
        result_graph_pattern: str,
        prefixes: dict | None = None,
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

    def call(self, binding_set: BindingSet, ki_name: str) -> BindingSet:
        """Invoke the handler of a registered KI by its name.

        Raises:
            KeyError: If ``ki_name`` is not found in the local KI registry.
        """
        ki_ctx = self.ki_registry[ki_name]
        assert ki_ctx.handler is not None  # Should always be set for ANSWER/REACT KI's

        dep_kwargs = resolve_dependencies(ki_ctx.handler)

        if ki_ctx.validation_model:
            binding_models = [
                ki_ctx.validation_model.model_validate(b) for b in binding_set
            ]
            result_bindings = ki_ctx.handler(binding_models, ki_ctx.info, **dep_kwargs)
        else:
            result_bindings = ki_ctx.handler(binding_set, ki_ctx.info, **dep_kwargs)

        if ki_ctx.serialization_model and result_bindings:
            # We can assume the result bindings are BindingModels, so we can model_dump
            result_bindings = [b.model_dump() for b in result_bindings]  # pyright: ignore[reportAttributeAccessIssue],
        return result_bindings  # pyright: ignore[reportReturnType]

    def post(
        self, binding_set: Sequence[BindingModel] | BindingSet, ki_name: str
    ) -> Sequence[BindingModel] | BindingSet:
        """Invoke a POST KI by its name.

        Raises:
            KeyError: If ``ki_name`` is not found in the local KI registry.
            ValueError: If the KI is not registered at the KE runtime.
        """
        ki_ctx = self.ki_registry[ki_name]
        if ki_ctx.info.type != KiTypes.POST:
            raise ValueError(
                f"KI named '{ki_name}' is of type {ki_ctx.info.type}, not POST, and "
                f"cannot be called with the post() method."
            )
        if ki_ctx.status != KnowledgeInteractionStatus.REGISTERED:
            raise ValueError(
                f"Cannot call KI '{ki_name}' because it is not registered. Please "
                f"register the KB and sync KIs first."
            )
        assert ki_ctx.info.id is not None  # Should always be set for registered KIs

        if ki_ctx.serialization_model:
            # We can assume the result bindings are BindingModels, so we can model_dump
            binding_models = [
                b.model_dump()  # pyright: ignore[reportAttributeAccessIssue]
                for b in binding_set
            ]
            post_result = self.client.post(
                kb_id=self.info.id,
                ki_id=ki_ctx.info.id,
                binding_set=binding_models,
            )
        else:
            post_result = self.client.post(
                kb_id=self.info.id,
                ki_id=ki_ctx.info.id,
                binding_set=binding_set,  # pyright: ignore[reportArgumentType]
            )

        if ki_ctx.validation_model and post_result.result_binding_set:
            result_bindings = [
                ki_ctx.validation_model.model_validate(b)
                for b in post_result.result_binding_set
            ]
            return result_bindings
        else:
            return post_result.result_binding_set

    def ask(
        self, binding_set: Sequence[BindingModel] | BindingSet, ki_name: str
    ) -> Sequence[BindingModel] | BindingSet:
        """..."""
        ki_ctx = self.ki_registry[ki_name]
        if ki_ctx.info.type != KiTypes.ASK:
            raise ValueError(
                f"KI named '{ki_name}' is of type {ki_ctx.info.type}, not ASK, and "
                f"cannot be called with the ask() method."
            )
        if ki_ctx.status != KnowledgeInteractionStatus.REGISTERED:
            raise ValueError(
                f"Cannot call KI '{ki_name}' because it is not registered. Please "
                f"register the KB and sync KIs first."
            )
        assert ki_ctx.info.id is not None  # Should always be set for registered KIs
        if ki_ctx.serialization_model:
            # We can assume the result bindings are BindingModels, so we can model_dump
            binding_models = [
                b.model_dump()  # pyright: ignore[reportAttributeAccessIssue]
                for b in binding_set
            ]
            ask_result = self.client.ask(
                kb_id=self.info.id,
                ki_id=ki_ctx.info.id,
                binding_set=binding_models,
            )
        else:
            ask_result = self.client.ask(
                kb_id=self.info.id,
                ki_id=ki_ctx.info.id,
                binding_set=binding_set,  # pyright: ignore[reportArgumentType]
            )

        if ki_ctx.validation_model and ask_result.binding_set:
            result_bindings = [
                ki_ctx.validation_model.model_validate(b)
                for b in ask_result.binding_set
            ]
            return result_bindings
        else:
            return ask_result.binding_set

    def start_handling_loop(self, loops: int | None = None) -> None:
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
            RuntimeError: If an unknown long-polling result is obtained from the KE
            client.
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
                    assert maybe_handle_request is not None
                    name = next(
                        ki.info.name
                        for ki in self.ki_registry.values()
                        if ki.info.id == maybe_handle_request.knowledge_interaction_id
                    )
                    result_binding_set = self.call(
                        maybe_handle_request.binding_set,
                        name,
                    )
                    self.client.post_handle_response(
                        kb_id=self.info.id,
                        ki_id=maybe_handle_request.knowledge_interaction_id,
                        handle_request_id=maybe_handle_request.handle_request_id,
                        binding_set=result_binding_set,
                    )

                case PollResult.REPOLL, None:
                    continue
                case PollResult.EXIT, None:
                    logger.info("Received exit signal from KE, stopping handling loop.")
                    return
                case _:
                    raise RuntimeError(
                        f"Unexpected poll result: {poll_result} or request:"
                        f"{maybe_handle_request}"
                    )

    @property
    def is_registered(self) -> bool:
        """Is the knowledge base in the registered state"""
        return self.state == KnowledgeBaseState.REGISTERED
