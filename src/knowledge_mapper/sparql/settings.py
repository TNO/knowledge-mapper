"""Settings for the ``knowledge-mapper sparql`` subcommand."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from ..ke.models import KnowledgeInteractionInfo
from ..settings import KnowledgeBaseSettings


class SparqlKnowledgeInteractionInfo(KnowledgeInteractionInfo):
    """A KI definition extended with SPARQL-specific fields.

    ``sparql_query`` is the SELECT query executed against the SPARQL endpoint
    when this KI is triggered.

    ``variable_mapping`` optionally maps graph-pattern variable names to SPARQL
    result variable names.  When omitted, a 1:1 name mapping is assumed (i.e.
    the SPARQL result variable ``?x`` maps to graph-pattern variable ``x``).
    """

    sparql_query: str
    variable_mapping: dict[str, str] | None = None


class SparqlSettings(KnowledgeBaseSettings):
    """Settings for a config-driven SPARQL-backed Knowledge Base.

    Extends :class:`~knowledge_mapper.settings.KnowledgeBaseSettings` with a
    ``sparql_endpoint`` URL and SPARQL-specific KI definitions.
    """

    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        json_file="config.json",
        env_nested_delimiter="__",
        extra="ignore",
    )

    sparql_endpoint: str
    knowledge_interactions: list[SparqlKnowledgeInteractionInfo] = Field(
        default_factory=list
    )
