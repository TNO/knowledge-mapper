import logging
from collections.abc import Callable
from functools import wraps
from typing import Concatenate

from pydantic import BaseModel

from .ke import Client
from .ke.errors import KnowledgeEngineNotAvailableError
from .ke.models import (
    AskAnswerInteractionInfo,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
)

logger = logging.getLogger(__name__)


type BindingSet = list[dict[str, str]]


class BindingModel(BaseModel):
    pass


type Handler = Callable[
    Concatenate[list[BindingModel], KnowledgeInteractionInfo, ...], list[BindingModel]
]


class KnowledgeBase:
    def __init__(self, id: str, name: str, description: str, ke_url: str):
        self.registered = False
        self.deferred_kis: list[KnowledgeInteractionInfo] = []
        self.ki_registry: dict[str, KnowledgeInteractionInfo] = {}
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
        self, ki_info: KnowledgeInteractionInfo, defer_registration: bool = False
    ) -> KnowledgeInteractionInfo:
        if defer_registration:
            self.deferred_kis.append(ki_info)
            return ki_info
        else:
            registered_ki = self.client.register_ki(
                kb_id=self.info.id,
                ki=ki_info,
            )
            self.ki_registry[registered_ki.id] = registered_ki
            return registered_ki

    def _register_ki_decorator(
        self, info: KnowledgeInteractionInfo, defer_registration: bool
    ) -> Callable[[Handler], Handler]:
        def decorator(func: Handler) -> Handler:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.register_ki(info, defer_registration=defer_registration)
            return wrapper

        return decorator

    def register_deferred_kis(self) -> None:
        for ki_info in self.deferred_kis:
            registered_ki = self.client.register_ki(
                kb_id=self.info.id,
                ki=ki_info,
            )
            self.ki_registry[registered_ki.id] = registered_ki
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

    def handle(
        self, binding_set: BindingSet, ki: KnowledgeInteractionInfo
    ) -> BindingSet:
        pass
