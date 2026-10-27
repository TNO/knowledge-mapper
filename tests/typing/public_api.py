# ruff: noqa: F401
"""Type-checked as a downstream consumer would see the package (see #82).

Checked by pyright in CI, not executed by pytest. Pyright only applies its
re-export rules (reportPrivateImportUsage) to installed typed packages, so it
must run with this directory as project root.
"""

from knowledge_mapper import (
    UNDEFINED,
    UNDEFINED_LITERAL,
    AnyExchangeInfo,
    AskExchangeInfo,
    BindingModel,
    BindingSet,
    Datatype,
    Depends,
    ExchangeInfo,
    ExchangeResult,
    KnowledgeBase,
    KnowledgeBaseBuilder,
    KnowledgeBaseId,
    KnowledgeBaseSettings,
    KnowledgeInteraction,
    KnowledgeInteractionId,
    Literal,
    PostExchangeInfo,
    RdfLiteral,
    UndefinedLiteral,
    Uri,
    __version__,
    get_requesting_kb_id,
    validate_kb_id,
)
from knowledge_mapper.ke import Client, ClientProtocol
from knowledge_mapper.testing import TestClient


def value_or_undefined(value: float | None) -> float | UndefinedLiteral:
    return UNDEFINED_LITERAL if value is None else value
