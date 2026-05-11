import logging

from .knowledge_base import KnowledgeBase
from .knowledge_base_builder import KnowledgeBaseBuilder
from .settings import KnowledgeBaseSettings

__version__ = "0.1.0a0"

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger(__name__).addHandler(_handler)
logging.getLogger(__name__).setLevel(logging.DEBUG)
