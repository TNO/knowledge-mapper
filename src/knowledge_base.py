import logging
from collections.abc import Callable
from functools import wraps

from .ke import Client
from .ke.errors import KnowledgeEngineNotAvailableError
from .ke.models import (
    AskAnswerInteractionInfo,
    BindingSet,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
)
from .knowledge_interaction import Handler, KnowledgeInteractionContext

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self, id: str, name: str, description: str, ke_url: str):
        self.registered = False
        self.deferred_kis: list[KnowledgeInteractionContext] = []
        self.ki_registry: dict[str, KnowledgeInteractionContext] = {}
        self.client = Client(ke_url)
        self.info = KnowledgeBaseInfo(
            id=id,
            name=name,
            description=description,
        )

    def connect(self) -> None:
        """Checks whether the KE runtime is available and raises an exception if not."""
        connected = self.client.ke_is_available()
        if not connected:
            raise KnowledgeEngineNotAvailableError(self.client.ke_url)

    def register(self) -> None:
        logger.info(
            "Registering knowledge base '%s' (%s).", self.info.id, self.info.name
        )
        self.client.register_kb(self.info)
        self.registered = True
        self.register_deferred_kis()
        return

    def unregister(self) -> None:
        logger.info(
            "Unregistering knowledge base '%s' (%s).", self.info.id, self.info.name
        )
        self.client.unregister_kb(self.info.id)
        self.registered = False
        return

    def register_ki(
        self, ki_ctx: KnowledgeInteractionContext, defer_registration: bool = False
    ) -> KnowledgeInteractionInfo:
        if defer_registration:
            self.deferred_kis.append(ki_ctx)
            return ki_ctx.info
        else:
            registered_ki = self.client.register_ki(
                kb_id=self.info.id,
                ki=ki_ctx.info,
            )
            ki_ctx.info = registered_ki
            self.ki_registry[registered_ki.id] = ki_ctx
            return registered_ki

    def _register_ki_decorator(
        self, info: KnowledgeInteractionInfo, defer_registration: bool
    ) -> Callable[[Handler], Handler]:
        def decorator(func: Handler) -> Handler:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.register_ki(
                KnowledgeInteractionContext(info=info, handler=func),
                defer_registration=defer_registration,
            )
            return wrapper

        return decorator

    def register_deferred_kis(self) -> None:
        for ki_ctx in self.deferred_kis:
            self.register_ki(ki_ctx, defer_registration=False)
        self.deferred_kis.clear()
        return

    def ask_ki(
        self,
        name: str,
        graph_pattern: str,
        prefixes: dict = None,
        defer_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        return self._register_ki_decorator(
            info=AskAnswerInteractionInfo(
                type=KiTypes.ASK,
                name=name,
                prefixes=prefixes or dict(),
                graph_pattern=graph_pattern,
            ),
            defer_registration=defer_registration,
        )

    def answer_ki(
        self,
        name: str,
        graph_pattern: str,
        prefixes: dict = None,
        defer_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        return self._register_ki_decorator(
            info=AskAnswerInteractionInfo(
                type=KiTypes.ANSWER,
                name=name,
                prefixes=prefixes or dict(),
                graph_pattern=graph_pattern,
            ),
            defer_registration=defer_registration,
        )

    def post_ki(
        self,
        name: str,
        argument_graph_pattern: str,
        result_graph_pattern: str,
        prefixes: dict = None,
        defer_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        return self._register_ki_decorator(
            info=PostReactInteractionInfo(
                type=KiTypes.POST,
                name=name,
                prefixes=prefixes or dict(),
                argument_graph_pattern=argument_graph_pattern,
                result_graph_pattern=result_graph_pattern,
            ),
            defer_registration=defer_registration,
        )

    def react_ki(
        self,
        name: str,
        argument_graph_pattern: str,
        result_graph_pattern: str,
        prefixes: dict = None,
        defer_registration: bool = True,
    ) -> Callable[[Handler], Handler]:
        return self._register_ki_decorator(
            info=PostReactInteractionInfo(
                type=KiTypes.REACT,
                name=name,
                prefixes=prefixes or dict(),
                argument_graph_pattern=argument_graph_pattern,
                result_graph_pattern=result_graph_pattern,
            ),
            defer_registration=defer_registration,
        )

    def call(self, binding_set: BindingSet, ki: KnowledgeInteractionInfo) -> BindingSet:
        if ki.id not in self.ki_registry:
            raise ValueError(f"Knowledge Interaction '{ki.name}' is not registered.")

        ki_ctx = self.ki_registry[ki.id]
        result = ki_ctx.handler(binding_set)
        return result
