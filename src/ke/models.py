from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

type BindingSet = list[dict[str, str]]


class BindingModel(BaseModel):
    pass


class KnowledgeBaseInfo(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)

    id: str = Field(..., alias="knowledgeBaseId")
    name: str = Field(..., alias="knowledgeBaseName")
    description: str = Field(..., alias="knowledgeBaseDescription")


class KiTypes(StrEnum):
    ASK = "AskKnowledgeInteraction"
    ANSWER = "AnswerKnowledgeInteraction"
    POST = "PostKnowledgeInteraction"
    REACT = "ReactKnowledgeInteraction"


class KnowledgeInteractionInfo(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, extra="allow", frozen=True, populate_by_name=True
    )

    type: KiTypes = Field(..., alias="knowledgeInteractionType")
    id: str | None = Field(default=None, alias="knowledgeInteractionId")
    name: str = Field(..., alias="knowledgeInteractionName")
    prefixes: dict[str, str] = Field(default_factory=dict)


class AskAnswerInteractionInfo(KnowledgeInteractionInfo):
    graph_pattern: str


class PostReactInteractionInfo(KnowledgeInteractionInfo):
    argument_graph_pattern: str
    result_graph_pattern: str
