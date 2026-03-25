import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Concatenate

from src.ke.models import BindingModel, KnowledgeInteractionInfo

type Handler = Callable[
    Concatenate[list[BindingModel], KnowledgeInteractionInfo, ...], list[BindingModel]
]

@dataclass
class KnowledgeInteractionContext:
    info: KnowledgeInteractionInfo
    handler: Handler

    def __post_init__(self):
        if not callable(self.handler):
            raise ValueError("Handler must be a callable.")
        
        sig = inspect.signature(self.handler)
        if "binding_set" not in sig.parameters:
            raise ValueError("Handler must have a 'binding_set' parameter.")
 