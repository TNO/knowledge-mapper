"""CLI example: define a KnowledgeBase and let ``knowledge-mapper run`` start it.

This file deliberately contains no ``asyncio.run`` boilerplate or
``if __name__ == "__main__"`` block. The CLI takes care of the full lifecycle —
connect, register, run the handling loop, and unregister on Ctrl+C.

Run with:

    knowledge-mapper run 10-cli.py:kb

(from the ``examples/`` directory, with the package installed). Press Ctrl+C
to stop; the CLI handles SIGINT/SIGTERM and shuts the KB down cleanly.
"""

from shared import get_example_logger

from knowledge_mapper import KnowledgeBase

EXAMPLE_NAME = "cli"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/cli#kb",
    name="example-cli-kb",
    description="A KB started via the knowledge-mapper CLI.",
    ke_url="http://localhost:8280/rest",
)


@kb.answer_ki(
    name="example-answer-ki",
    graph_pattern="""
        ?question a ex:Question .
        ?question ex:hasText ?text .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/cli#"},
)
def example_answer_ki(binding_set, info):
    logger.info("Handling a call to the example answer KI.")
    return binding_set
