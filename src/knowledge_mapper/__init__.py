import logging

from .dependency_injection import Depends, get_requesting_kb_id
from .kb.builder import KnowledgeBaseBuilder
from .kb.knowledge_base import KnowledgeBase
from .ke.models import (
    UNDEFINED,
    UNDEFINED_LITERAL,
    AnyExchangeInfo,
    AskExchangeInfo,
    BindingModel,
    BindingSet,
    Datatype,
    ExchangeInfo,
    KnowledgeBaseId,
    KnowledgeInteraction,
    KnowledgeInteractionId,
    Literal,
    PostExchangeInfo,
    RdfLiteral,
    Uri,
    validate_kb_id,
)
from .knowledge_interaction import ExchangeResult
from .settings import KnowledgeBaseSettings

__version__ = "0.1.0rc1"

# The package attaches its own handler/formatter so log output is sensible
# out of the box, even if the host application never calls
# `logging.basicConfig()`. Propagation to ancestor loggers (e.g. the root
# logger, which the host application may configure separately) is disabled
# so records aren't emitted twice -- once via this handler, once via the
# host's. Host applications that want to fully control formatting/handling of
# knowledge_mapper's log records can remove `_handler` from this logger (or
# re-enable propagate) and configure the root logger instead.
_logger = logging.getLogger(__name__)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG)
_logger.propagate = False
