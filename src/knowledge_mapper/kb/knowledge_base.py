from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable, Sequence
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any

from ..ke import Client
from ..ke.client import ClientProtocol, HandleRequest, PollResult
from ..ke.errors import KnowledgeEngineNotAvailableError
from ..ke.models import (
    AskAnswerKnowledgeInteraction,
    BindingModel,
    BindingSet,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteraction,
    KnowledgeInteractionInfo,
    PostReactKnowledgeInteraction,
    SmartConnectorLease,
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

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        ke_url: str,
        lease_renewal_time: int | None = None,
        reasoner_level: int | None = None,
    ):
        self.state = KnowledgeBaseState.UNREGISTERED
        self.ki_registry: dict[str, KnowledgeInteractionContext[Any, ...]] = {}
        self._ki_registry_by_id: dict[str, KnowledgeInteractionContext[Any, ...]] = {}
        self.client: ClientProtocol = Client(ke_url)
        self.info = KnowledgeBaseInfo(
            id=id,
            name=name,
            description=description,
            lease_renewal_time=lease_renewal_time,
            reasoner_level=reasoner_level,
        )
        self.dependency_overrides: dict[Callable[..., Any], Callable[..., Any]] = {}

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

    async def connect(self) -> None:
        """Checks whether the KE runtime is available and raises an exception if not.

        Raises:
            KnowledgeEngineNotAvailableError: If the KE runtime cannot be reached.
        """
        if not await self.client.ke_is_available():
            raise KnowledgeEngineNotAvailableError(self.client.ke_url)

    async def register(self) -> None:
        """Register this knowledge base at the KE runtime, reregister if already
        registered. Automatically syncs knowledge interactions with KE runtime.

        Raises:
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
            response.
        """
        logger.info(
            "Registering knowledge base '%s' (%s).", self.info.id, self.info.name
        )
        await self.client.register_kb(self.info, reregister=True)
        self.state = KnowledgeBaseState.REGISTERED
        await self.sync_knowledge_interactions()
        return

    async def unregister(self) -> None:
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
        await self.client.unregister_kb(self.info.id)
        self.state = KnowledgeBaseState.UNREGISTERED
        self._ki_registry_by_id.clear()
        for ki_ctx in self.ki_registry.values():
            ki_ctx.status = KnowledgeInteractionStatus.UNREGISTERED
        return

    def _register_ki_locally(
        self,
        ki_ctx: KnowledgeInteractionContext[Any, ...],
    ) -> None:
        """Validate and store a KI context in the local registry (sync).

        Does NOT contact the KE runtime. Use :meth:`register_ki` for full
        async registration, or call this from synchronous code (e.g. decorators)
        followed by :meth:`sync_knowledge_interactions` to push to the KE.
        """
        if ki_ctx.definition.name in (
            ki.definition.name for ki in self.ki_registry.values()
        ):
            raise ValueError(
                f"A KI named '{ki_ctx.definition.name}' is already registered for "
                f"this KB."
            )
        if ki_ctx.status == KnowledgeInteractionStatus.REGISTERED:
            raise ValueError(
                f"Cannot register KI '{ki_ctx.definition.name}' because it is "
                f"already registered."
            )
        self.ki_registry[ki_ctx.definition.name] = ki_ctx

    async def register_ki(
        self,
        ki_ctx: KnowledgeInteractionContext[Any, ...],
        defer_ke_registration: bool = False,
    ) -> KnowledgeInteractionInfo | None:
        """Register a knowledge interaction for this knowledge base at the KE runtime
        and store it in this object's registry of interactions.

        Returns the :class:`KnowledgeInteractionInfo` reported by the KE, or ``None``
        if ``defer_ke_registration`` is ``True`` (in which case no KE call was made).

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
                f"Cannot register KI '{ki_ctx.definition.name}' because the KB is "
                f"not registered. Consider setting defer_ke_registration=True to "
                f"defer registration until the KB itself is registered."
            )

        self._register_ki_locally(ki_ctx)

        if defer_ke_registration:
            return None

        registered_ki = await self.client.register_ki(
            kb_id=self.info.id,
            ki=ki_ctx.definition,
        )
        ki_ctx.ke_id = registered_ki.id
        ki_ctx.status = KnowledgeInteractionStatus.REGISTERED
        self._ki_registry_by_id[registered_ki.id] = ki_ctx
        return registered_ki

    def _register_ki_decorator(
        self, definition: KnowledgeInteraction, defer_ke_registration: bool
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
            if inspect.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(
                    binding_set: BindingSet | list[BindingModel],
                    info: KnowledgeInteraction,
                    *args,
                    **kwargs,
                ) -> BindingSet | Sequence[BindingModel]:
                    return await func(binding_set, info, *args, **kwargs)

                self._register_ki_locally(
                    KnowledgeInteractionContext(
                        definition=definition,
                        handler=async_wrapper,
                        status=KnowledgeInteractionStatus.UNREGISTERED,
                    ),
                )
                return async_wrapper
            else:

                @wraps(func)
                def wrapper(
                    binding_set: BindingSet | list[BindingModel],
                    info: KnowledgeInteraction,
                    *args,
                    **kwargs,
                ) -> BindingSet | Sequence[BindingModel]:
                    return func(binding_set, info, *args, **kwargs)  # pyright: ignore[reportReturnType]

                self._register_ki_locally(
                    KnowledgeInteractionContext(
                        definition=definition,
                        handler=wrapper,
                        status=KnowledgeInteractionStatus.UNREGISTERED,
                    ),
                )
                return wrapper

        return decorator

    async def sync_knowledge_interactions(self) -> None:
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
            registered_ki = await self.client.register_ki(
                kb_id=self.info.id,
                ki=ki_ctx.definition,
            )
            ki_ctx.ke_id = registered_ki.id
            ki_ctx.status = KnowledgeInteractionStatus.REGISTERED
            self._ki_registry_by_id[registered_ki.id] = ki_ctx
        return

    async def unregister_ki(self, ki_name: str) -> None:
        """Unregister a single knowledge interaction by name from this KB at the KE
        runtime, and remove it from this object's local registry.

        Raises:
            ValueError: If the KB is not registered, or if ``ki_name`` is unknown, or
                if the KI is not currently registered at the KE runtime.
            SmartConnectorNotFoundError: If the KB's smart connector or the KI is not
                found in the KE runtime.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
                response.
        """
        if self.state != KnowledgeBaseState.REGISTERED:
            raise ValueError(
                f"Cannot unregister KI '{ki_name}' because the KB is not registered."
            )
        if ki_name not in self.ki_registry:
            raise ValueError(
                f"Cannot unregister KI '{ki_name}': no KI with that name is "
                f"registered for this KB."
            )
        ki_ctx = self.ki_registry[ki_name]
        if (
            ki_ctx.status != KnowledgeInteractionStatus.REGISTERED
            or ki_ctx.ke_id is None
        ):
            raise ValueError(
                f"Cannot unregister KI '{ki_name}' because it is not currently "
                f"registered at the KE runtime."
            )

        logger.info("Unregistering KI '%s' (%s).", ki_name, ki_ctx.ke_id)
        await self.client.unregister_ki(kb_id=self.info.id, ki_id=ki_ctx.ke_id)
        self._ki_registry_by_id.pop(ki_ctx.ke_id, None)
        self.ki_registry.pop(ki_name, None)

    async def renew_lease(self) -> SmartConnectorLease:
        """Renew this KB's smart connector lease at the KE runtime and return the new
        lease.

        Raises:
            ValueError: If the KB is not registered.
            SmartConnectorNotFoundError: If the KB's smart connector is not found in
                the KE runtime, or it does not have a lease.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
                response.
        """
        if self.state != KnowledgeBaseState.REGISTERED:
            raise ValueError("Cannot renew lease because the KB is not registered.")
        logger.debug("Renewing lease for KB '%s'.", self.info.id)
        return await self.client.renew_lease(kb_id=self.info.id)

    async def load_domain_knowledge(self, knowledge: str) -> None:
        """Load domain knowledge (Apache Jena facts/rules) into this KB's smart
        connector. Replaces any previously loaded domain knowledge.

        Args:
            knowledge: The domain knowledge (facts and rules) as plain text in the
                Apache Jena Rules syntax.

        Raises:
            ValueError: If the KB is not registered.
            SmartConnectorNotFoundError: If the KB's smart connector is not found in
                the KE runtime.
            UnexpectedHttpResponseError: If the KE runtime returns an unexpected HTTP
                response.
        """
        if self.state != KnowledgeBaseState.REGISTERED:
            raise ValueError(
                "Cannot load domain knowledge because the KB is not registered."
            )
        logger.debug("Loading domain knowledge for KB '%s'.", self.info.id)
        await self.client.load_domain_knowledge(kb_id=self.info.id, knowledge=knowledge)

    def ki_from_definition(
        self,
        definition: KnowledgeInteraction,
        defer_ke_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        """Return a decorator that registers the decorated function as a KI handler
        based on the provided :class:`KnowledgeInteraction` definition.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
              violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        return self._register_ki_decorator(
            definition=definition, defer_ke_registration=defer_ke_registration
        )

    def ask_ki(
        self,
        name: str,
        graph_pattern: str,
        binding_model: type[BindingModel] | None = None,
        prefixes: dict | None = None,
        defer_ke_registration: bool = True,
    ) -> None:
        """Register an ASK KI on this KB. Call :meth:`ask` to query the network.

        Raises:
            ValueError: Propagated from ``register_ki`` if registration constraints are
            violated.
            SmartConnectorNotFoundError: Propagated from ``register_ki`` when contacting
              the KE runtime.
            UnexpectedHttpResponseError: Propagated from ``register_ki`` when contacting
              the KE runtime.
        """
        self._register_ki_locally(
            KnowledgeInteractionContext(
                definition=AskAnswerKnowledgeInteraction(
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
            definition=AskAnswerKnowledgeInteraction(
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
        result_graph_pattern: str | None = None,
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
        self._register_ki_locally(
            KnowledgeInteractionContext(
                definition=PostReactKnowledgeInteraction(
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
        )
        return

    def react_ki(
        self,
        name: str,
        argument_graph_pattern: str,
        result_graph_pattern: str | None = None,
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
            definition=PostReactKnowledgeInteraction(
                type=KiTypes.REACT,
                name=name,
                prefixes=prefixes or dict(),
                argument_graph_pattern=argument_graph_pattern,
                result_graph_pattern=result_graph_pattern,
            ),
            defer_ke_registration=defer_ke_registration,
        )

    async def call(self, binding_set: BindingSet, ki_name: str) -> BindingSet:
        """Invoke the handler of a registered KI by its name.

        Raises:
            KeyError: If ``ki_name`` is not found in the local KI registry.
        """
        return await self.ki_registry[ki_name].dispatch(
            binding_set,
            dependency_overrides=self.dependency_overrides or None,
        )

    async def post(
        self, binding_set: Sequence[BindingModel] | BindingSet, ki_name: str
    ) -> Sequence[BindingModel] | BindingSet:
        """Invoke a POST KI by its name.

        Raises:
            KeyError: If ``ki_name`` is not found in the local KI registry.
            ValueError: If the KI is not registered at the KE runtime.
        """
        ki_ctx = self.ki_registry[ki_name]
        if ki_ctx.definition.type != KiTypes.POST:
            raise ValueError(
                f"KI named '{ki_name}' is of type {ki_ctx.definition.type}, not "
                f"POST, and cannot be called with the post() method."
            )
        if ki_ctx.status != KnowledgeInteractionStatus.REGISTERED:
            raise ValueError(
                f"Cannot call KI '{ki_name}' because it is not registered. Please "
                f"register the KB and sync KIs first."
            )
        assert ki_ctx.ke_id is not None  # Should always be set for registered KIs

        post_result = await self.client.post(
            kb_id=self.info.id,
            ki_id=ki_ctx.ke_id,
            binding_set=ki_ctx.prepare_outgoing(binding_set),
        )
        return ki_ctx.parse_result(post_result.result_binding_set)

    async def ask(
        self, binding_set: Sequence[BindingModel] | BindingSet, ki_name: str
    ) -> Sequence[BindingModel] | BindingSet:
        """Invoke an ASK KI by its name.

        Raises:
            KeyError: If ``ki_name`` is not found in the local KI registry.
            ValueError: If the KI is not registered at the KE runtime.
        """
        ki_ctx = self.ki_registry[ki_name]
        if ki_ctx.definition.type != KiTypes.ASK:
            raise ValueError(
                f"KI named '{ki_name}' is of type {ki_ctx.definition.type}, not "
                f"ASK, and cannot be called with the ask() method."
            )
        if ki_ctx.status != KnowledgeInteractionStatus.REGISTERED:
            raise ValueError(
                f"Cannot call KI '{ki_name}' because it is not registered. Please "
                f"register the KB and sync KIs first."
            )
        assert ki_ctx.ke_id is not None  # Should always be set for registered KIs

        ask_result = await self.client.ask(
            kb_id=self.info.id,
            ki_id=ki_ctx.ke_id,
            binding_set=ki_ctx.prepare_outgoing(binding_set),
        )
        return ki_ctx.parse_result(ask_result.binding_set)

    def _require_loop(self) -> asyncio.AbstractEventLoop:
        """Return the stored event loop or raise if the handling loop is not running."""
        try:
            loop = self._loop
        except AttributeError:
            loop = None
        if loop is None:
            raise RuntimeError(
                "ask_sync() / post_sync() are only available from within a sync "
                "handler running inside the handling loop. Start the handling loop "
                "with start_handling_loop() first."
            )
        return loop

    def ask_sync(
        self,
        binding_set: Sequence[BindingModel] | BindingSet,
        ki_name: str,
    ) -> Sequence[BindingModel] | BindingSet:
        """Blocking bridge to :meth:`ask` for use in sync handlers.

        Schedules the async ``ask()`` coroutine on the event loop stored by
        :meth:`start_handling_loop` and blocks the calling thread until the
        result is ready.

        Raises:
            RuntimeError: If called outside the handling loop context.
        """
        loop = self._require_loop()
        future = asyncio.run_coroutine_threadsafe(
            self.ask(binding_set, ki_name=ki_name), loop
        )
        return future.result()

    def post_sync(
        self,
        binding_set: Sequence[BindingModel] | BindingSet,
        ki_name: str,
    ) -> Sequence[BindingModel] | BindingSet:
        """Blocking bridge to :meth:`post` for use in sync handlers.

        Schedules the async ``post()`` coroutine on the event loop stored by
        :meth:`start_handling_loop` and blocks the calling thread until the
        result is ready.

        Raises:
            RuntimeError: If called outside the handling loop context.
        """
        loop = self._require_loop()
        future = asyncio.run_coroutine_threadsafe(
            self.post(binding_set, ki_name=ki_name), loop
        )
        return future.result()

    async def start_handling_loop(
        self,
        loops: int | None = None,
        max_concurrent_handlers: int = 10,
    ) -> None:
        """Poll the KE runtime for incoming KI calls and dispatch them concurrently.

        Runs multiple concurrent poll-dispatch cycles, bounded by a semaphore.
        Each cycle acquires the semaphore, polls, and on HANDLE spawns a task
        that runs the handler, posts the response, and releases the semaphore.

        Stops when an EXIT signal is received or ``loops`` poll cycles have
        been completed.  On EXIT, all in-flight handler tasks are awaited
        before returning.

        Args:
            loops: If set, limits the total number of poll cycles (useful for
                testing).  ``None`` means poll indefinitely.
            max_concurrent_handlers: Maximum number of concurrent handler tasks
                (semaphore size).  Defaults to 10.

        Raises:
            RuntimeError: If the KB is not registered.
        """
        import asyncio

        if self.state != KnowledgeBaseState.REGISTERED:
            raise RuntimeError(
                "Cannot start handling loop because the KB is not registered. Please "
                "register the KB first."
            )

        self._loop = asyncio.get_running_loop()
        semaphore = asyncio.Semaphore(max_concurrent_handlers)
        in_flight: set[asyncio.Task[None]] = set()

        loops_done = 0
        while loops is None or loops_done < loops:
            await semaphore.acquire()
            loops_done += 1

            poll_result, maybe_handle_request = await self.client.poll_ki_call(
                kb_id=self.info.id
            )
            match poll_result, maybe_handle_request:
                case PollResult.HANDLE, _:
                    assert maybe_handle_request is not None

                    async def _handle(
                        handle_request: HandleRequest,
                    ) -> None:
                        try:
                            ki_id = handle_request.knowledge_interaction_id
                            ki_ctx = self._ki_registry_by_id[ki_id]
                            try:
                                result_binding_set = await self.call(
                                    handle_request.binding_set,
                                    ki_ctx.definition.name,
                                )
                            except Exception:
                                logger.exception(
                                    "Handler for KI '%s' raised an exception "
                                    "(request %d from %s). Posting empty binding set.",
                                    ki_ctx.definition.name,
                                    handle_request.handle_request_id,
                                    handle_request.requesting_knowledge_base_id,
                                )
                                result_binding_set = []

                            try:
                                await self.client.post_handle_response(
                                    kb_id=self.info.id,
                                    ki_id=handle_request.knowledge_interaction_id,
                                    handle_request_id=handle_request.handle_request_id,
                                    binding_set=result_binding_set,
                                )
                            except Exception:
                                logger.exception(
                                    "Failed to post handle response for KI '%s' "
                                    "(request %d from %s).",
                                    ki_ctx.definition.name,
                                    handle_request.handle_request_id,
                                    handle_request.requesting_knowledge_base_id,
                                )
                        finally:
                            semaphore.release()

                    task = asyncio.create_task(_handle(maybe_handle_request))
                    in_flight.add(task)
                    task.add_done_callback(in_flight.discard)

                case PollResult.REPOLL, None:
                    semaphore.release()
                    continue

                case PollResult.EXIT, None:
                    semaphore.release()
                    logger.info("Received exit signal from KE, stopping handling loop.")
                    break

                case _:
                    semaphore.release()
                    raise RuntimeError(
                        f"Unexpected poll result: {poll_result} or request:"
                        f"{maybe_handle_request}"
                    )

        if in_flight:
            await asyncio.gather(*in_flight)

    async def close(self) -> None:
        """Close the underlying client, releasing any held resources."""
        await self.client.close()

    @property
    def is_registered(self) -> bool:
        """Is the knowledge base in the registered state"""
        return self.state == KnowledgeBaseState.REGISTERED
