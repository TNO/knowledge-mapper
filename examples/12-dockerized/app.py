"""Dockerized example: an ANSWER knowledge base that runs inside a container.

The KB logic is deliberately minimal (it answers with a fixed list of greetings);
the point of this example is the Docker workflow around it. See README.md.

Nothing environment-specific is hard-coded: the KB identity and the Smart Connector
URL are read from environment variables by ``KnowledgeBaseSettings`` (nested fields
use ``__`` as delimiter), so the same image can be deployed anywhere:

    KNOWLEDGE_BASE__ID, KNOWLEDGE_BASE__NAME, KNOWLEDGE_BASE__DESCRIPTION,
    KNOWLEDGE_ENGINE_ENDPOINT

The container starts it with ``knowledge-mapper run app.py:kb``; the CLI handles
connect, register, the handling loop and unregistering on SIGTERM (``docker stop``).
"""

import logging

from knowledge_mapper import (
    BindingSet,
    KnowledgeBase,
    KnowledgeBaseSettings,
    KnowledgeInteraction,
)

# This file is copied into the image on its own, so it mirrors the logging helper in
# examples/shared.py instead of importing it.
logger = logging.getLogger("dockerized-example")
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] [dockerized-example] %(message)s")
)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

settings = KnowledgeBaseSettings()  # type: ignore[call-arg]
kb = KnowledgeBase.from_settings(settings).build()


@kb.answer_ki(
    name="greeting-answer-ki",
    graph_pattern="""
        ?greeting a ex:Greeting ;
            ex:hasText ?text .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/dockerized#"},
)
def greeting_answer_ki(
    binding_set: BindingSet, info: KnowledgeInteraction
) -> BindingSet:
    logger.info(f"Answering a greeting request with bindings: {binding_set}")
    return [
        {
            "greeting": "<http://example.org/knowledge-mapper/dockerized#hello>",
            "text": '"Hello from a container!"',
        },
        {
            "greeting": "<http://example.org/knowledge-mapper/dockerized#goedemorgen>",
            "text": '"Goedemorgen vanuit een container!"',
        },
    ]
