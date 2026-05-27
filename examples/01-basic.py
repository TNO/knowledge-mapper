"""Basic example: register a simple ANSWER KI and handle incoming requests.

This is the smallest runnable example and a good starting point to understand the
KnowledgeBase lifecycle: connect -> register -> unregister.
"""

from shared import get_example_logger

from knowledge_mapper import KnowledgeBase

EXAMPLE_NAME = "basic"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/basic#kb",
    name="example-kb",
    description="A simple example KB for demonstration purposes.",
    ke_url="http://localhost:8280/rest",
)


# Decorate a function as an ANSWER KI handler.
# The incoming bindings match the graph pattern variables.
@kb.answer_ki(
    name="example-answer-ki",
    graph_pattern="""
        ?question a ex:Question .
        ?question ex:hasText ?text .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/basic#"},
)
def example_answer_ki(binding_set, info):
    logger.info("Handling a call to the example answer KI.")
    # Echo incoming bindings to demonstrate a minimal handler.
    return binding_set


async def main():
    # Connect to the KE, then register and unregister this KB.
    await kb.connect()
    await kb.register()
    logger.info("Registered a Knowledge Base in the basic example!")
    await kb.unregister()
    logger.info("Unregistered the Knowledge Base in the basic example!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
