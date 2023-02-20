import os
import json
import logging
from knowledge_mapper.knowledge_interaction import (
    AnswerKnowledgeInteraction,
    AnswerKnowledgeInteractionRegistrationRequest,
)
from knowledge_mapper.tke_client import TkeClient
from knowledge_mapper.utils import match_bindings
from knowledge_mapper.knowledge_base import KnowledgeBaseRegistrationRequest


logger = logging.getLogger(__name__)

KE_API = os.environ.get("KE_API")
KB_ID = os.environ.get("KB_ID")
KB_NAME = os.environ.get("KB_NAME")
KB_DESCRIPTION = os.environ.get("KB_DESCRIPTION")
GRAPH_PATTERN = os.environ.get("GRAPH_PATTERN")
GRAPH_PATTERN_PREFIXES = os.environ.get("GRAPH_PATTERN_PREFIXES")
SOURCE_DATA = json.loads(os.environ.get("SOURCE_JSON_DATA"))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = TkeClient(KE_API)
    logger.info(f"going to register knowledge base")
    client.connect()

    kb = client.register(
        KnowledgeBaseRegistrationRequest(
            id=KB_ID,
            name=KB_NAME,
            description=KB_DESCRIPTION,
        )
    )

    logger.info(f"registered knowledge base")
    logger.info(SOURCE_DATA)

    def handler(bindings: list[dict[str, str]], requesting_kb_id: str):
        logger.info(f"processing bindings from {requesting_kb_id}")
        if not bindings:
            bindings = [{}]
        return match_bindings(bindings, SOURCE_DATA)

    ki: AnswerKnowledgeInteraction = kb.register_knowledge_interaction(
        AnswerKnowledgeInteractionRegistrationRequest(
            pattern=GRAPH_PATTERN,
            prefixes=json.loads(GRAPH_PATTERN_PREFIXES),
            handler=handler,
        )
    )

    kb.start_handle_loop()
