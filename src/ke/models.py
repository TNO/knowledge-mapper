from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Any, Self, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
)
from pydantic.alias_generators import to_camel
from rdflib import Literal as RDFLiteral
from rdflib import URIRef
from rdflib.util import from_n3

type BindingSet = Sequence[dict[str, str]]

# region:    -- Binding Node


def validate_uri(input: str | URIRef | None) -> URIRef | None:
    if isinstance(input, URIRef) or input is None:
        return input
    uri = from_n3(input)
    if not isinstance(uri, URIRef):
        raise ValueError(f"Expected a URIRef value, got {input}")
    return uri


def serialize_uri(input: URIRef | None) -> str | None:
    if input is None:
        return None
    return input.n3()


Uri = Annotated[
    URIRef | None,
    PlainValidator(validate_uri),
    PlainSerializer(serialize_uri),
    Field(default=None),
]


def serialize_literal(input: Any) -> str | None:
    if input is None:
        return None
    return RDFLiteral(input).n3()


def validate_literal(input: Any) -> Any:
    if isinstance(input, RDFLiteral):
        return input.toPython()
    if input is None:
        return None
    if not isinstance(input, str) or not (
        input.startswith('"') or input.startswith("'")
    ):
        return input

    literal = from_n3(input)
    if not isinstance(literal, RDFLiteral):
        raise ValueError(f"Expected a literal value, got {input}")
    return literal.toPython()


T = TypeVar("T")
Literal = Annotated[
    T | None,
    PlainSerializer(serialize_literal),
    BeforeValidator(validate_literal),
    Field(default=None),
]

# endregion: -- Binding Node

# region:    -- Binding Model


class BindingModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True, alias_generator=to_camel, populate_by_name=True
    )

    def dump_result_binding(self) -> dict[str, Any]:
        if any([data is None for _, data in self]):
            raise ValueError(
                "Model cannot contain unset fields when dumping to outgoing binding"
            )
        return self.model_dump(by_alias=True)

    def dump_partial_binding(self, exclude_none: bool = True) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=exclude_none)

    def matches_with(self, **kwargs) -> bool:
        for key, other_value in kwargs.items():
            own_value = getattr(self, key)
            if own_value is None:
                continue
            if own_value.n3() == other_value:
                continue
            return False
        return True

    def matches_with_binding(self, binding: Self) -> bool:
        return self.matches_with(**binding.model_dump(exclude_none=True))


class KnowledgeBaseInfo(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)

    id: Annotated[str, Field(..., alias="knowledgeBaseId")]
    name: Annotated[str, Field(..., alias="knowledgeBaseName")]
    description: Annotated[str, Field(..., alias="knowledgeBaseDescription")]


class KiTypes(StrEnum):
    ASK = "AskKnowledgeInteraction"
    ANSWER = "AnswerKnowledgeInteraction"
    POST = "PostKnowledgeInteraction"
    REACT = "ReactKnowledgeInteraction"


class KnowledgeInteractionInfo(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, extra="allow", frozen=True, populate_by_name=True
    )

    type: Annotated[KiTypes, Field(..., alias="knowledgeInteractionType")]
    id: Annotated[str | None, Field(..., alias="knowledgeInteractionId")] = None
    name: Annotated[str, Field(..., alias="knowledgeInteractionName")]
    prefixes: Annotated[dict[str, str], Field(default_factory=dict)]


class AskAnswerInteractionInfo(KnowledgeInteractionInfo):
    graph_pattern: str


class PostReactInteractionInfo(KnowledgeInteractionInfo):
    argument_graph_pattern: str
    result_graph_pattern: str
