import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Concatenate, get_args

from .dependency_injection import resolve_dependencies
from .ke.models import BindingModel, BindingSet, KiTypes, KnowledgeInteractionInfo

type Handler[B, **P] = Callable[
    Concatenate[B, KnowledgeInteractionInfo, P],
    BindingSet | Sequence[BindingModel],
]


class KnowledgeInteractionStatus(StrEnum):
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"


@dataclass
class KnowledgeInteractionContext[B, **P]:
    info: KnowledgeInteractionInfo
    handler: Handler[B, P] | None
    status: KnowledgeInteractionStatus = KnowledgeInteractionStatus.UNREGISTERED
    validation_model: type[BindingModel] | None = None
    serialization_model: type[BindingModel] | None = None

    def __post_init__(self):
        if self.info.type == KiTypes.ANSWER or self.info.type == KiTypes.REACT:
            if not callable(self.handler):
                raise ValueError("Handler must be a callable.")

            self.validation_model = self._inspect_incoming_binding_model(self.handler)
            self.serialization_model = self._inspect_outgoing_binding_model(
                self.handler
            )

    def dispatch(self, binding_set: BindingSet) -> BindingSet:
        """Validate incoming bindings, call the handler (with DI), and serialize
        the result back to a raw BindingSet.

        Used by the handling loop for incoming ANSWER/REACT KI calls.
        """
        assert self.handler is not None

        dep_kwargs = resolve_dependencies(self.handler)

        if self.validation_model:
            validated = [self.validation_model.model_validate(b) for b in binding_set]
            result_bindings = self.handler(validated, self.info, **dep_kwargs)
        else:
            result_bindings = self.handler(binding_set, self.info, **dep_kwargs)

        if self.serialization_model and result_bindings:
            return [b.model_dump() for b in result_bindings]  # pyright: ignore[reportAttributeAccessIssue]
        return result_bindings  # pyright: ignore[reportReturnType]

    def prepare_outgoing(
        self, binding_set: Sequence[BindingModel] | BindingSet
    ) -> BindingSet:
        """Serialize outgoing BindingModels to raw dicts for the client.

        Used by ``ask()`` / ``post()`` before calling the SC.
        """
        if self.serialization_model:
            return [b.model_dump() for b in binding_set]  # pyright: ignore[reportAttributeAccessIssue]
        return binding_set  # pyright: ignore[reportReturnType]

    def parse_result(
        self, binding_set: BindingSet
    ) -> Sequence[BindingModel] | BindingSet:
        """Validate raw result bindings into BindingModels if a validation model
        is configured.

        Used by ``ask()`` / ``post()`` after receiving the SC response.
        """
        if self.validation_model and binding_set:
            return [self.validation_model.model_validate(b) for b in binding_set]
        return binding_set

    def _inspect_incoming_binding_model(
        self, handler: Callable[..., Any]
    ) -> type[BindingModel] | None:
        signature = inspect.signature(handler)
        if "binding_set" not in signature.parameters:
            raise ValueError("Handler must have a 'binding_set' parameter.")

        binding_set_param = signature.parameters["binding_set"]
        if binding_set_param.annotation is inspect.Parameter.empty:
            # No incoming binding model is provided, assume a raw BindingSet
            return None

        err = ValueError(
            "Handler 'binding_set' parameter must be annotated with BindingSet "
            "or a Sequence of BindingModels."
        )
        annotation = binding_set_param.annotation
        origin = getattr(annotation, "__origin__", None)
        if origin is not None and issubclass(origin, Sequence):
            item_type = get_args(annotation)[0]
            if not isinstance(item_type, type):
                # Error if binding_set annotation is a Sequence but item type is not a
                # class
                raise err

            if issubclass(item_type, BindingModel):
                # Incoming binding model is provided
                return item_type
            elif isinstance(item_type, dict):
                # No incoming binding model is provided, just a raw BindingSet
                return None
            else:
                # Error if binding_set annotation is a Sequence but item type is not a
                # BindingModel or a dict
                raise err
        elif origin is None and isinstance(annotation, type):
            # Error if return type annotation is not a Sequence of BindingModels or a
            # raw BindingSet
            raise err
        else:
            # No outgoing binding model is provided, just a raw BindingSet
            return None

    def _inspect_outgoing_binding_model(
        self, handler: Callable[..., Any]
    ) -> type[BindingModel] | None:
        signature = inspect.signature(handler)
        if signature.return_annotation is inspect.Signature.empty:
            return None

        err = ValueError(
            "Handler return type must be annotated with BindingSet or a Sequence of "
            "BindingModels."
        )
        annotation = signature.return_annotation
        origin = getattr(annotation, "__origin__", None)
        if origin is not None and issubclass(origin, Sequence):
            item_type = get_args(annotation)[0]
            if not isinstance(item_type, type):
                # Error if return type annotation is a Sequence but item type is not a
                # class
                raise err

            if issubclass(item_type, BindingModel):
                # Outgoing binding model is provided
                return item_type
            elif isinstance(item_type, dict):
                # No outgoing binding model is provided, just a raw BindingSet
                return None
            else:
                # Error if return type annotation is a Sequence but item type is not a
                # BindingModel or a dict
                raise err
        elif origin is None and isinstance(annotation, type):
            # Error if return type annotation is not a Sequence of BindingModels or a
            # raw BindingSet
            raise err
        else:
            # No outgoing binding model is provided, just a raw BindingSet
            return None
