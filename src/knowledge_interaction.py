import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Concatenate

from src.ke.models import BindingSet, KnowledgeInteractionInfo

type Handler = Callable[
    Concatenate[BindingSet, KnowledgeInteractionInfo, ...], BindingSet
]


def default_ask_handler(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    # TODO: Implement a default ASK handler when implementing serialization and
    # validation of binding sets
    raise NotImplementedError(
        "default_ask_handler is not yet implemented. "
        "Provide a custom handler via ki_from_settings instead."
    )


def default_post_handler(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    # TODO: Implement a default POST handler when implementing serialization and
    # validation of binding sets
    raise NotImplementedError(
        "default_post_handler is not yet implemented. "
        "Provide a custom handler via ki_from_settings instead."
    )


class KnowledgeInteractionStatus(StrEnum):
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"


@dataclass
class KnowledgeInteractionContext:
    info: KnowledgeInteractionInfo
    handler: Handler
    status: KnowledgeInteractionStatus = KnowledgeInteractionStatus.UNREGISTERED

    def __post_init__(self):
        if not callable(self.handler):
            raise ValueError("Handler must be a callable.")

        sig = inspect.signature(self.handler)
        if "binding_set" not in sig.parameters:
            raise ValueError("Handler must have a 'binding_set' parameter.")
