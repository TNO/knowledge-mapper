from shared import get_example_logger

from src.knowledge_base import KnowledgeBase

EXAMPLE_NAME = "basic"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/basic#kb",
    name="example-kb",
    description="A simple example KB for demonstration purposes.",
    ke_url="http://localhost:8280/rest",
)


@kb.answer_ki(
    name="example-answer-ki",
    graph_pattern="""
        ?question a ex:Question .
        ?question ex:hasText ?text .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/basic#"},
)
def example_answer_ki():
    logger.info("Handling a call to the example answer KI.")


if __name__ == "__main__":
    kb.connect()
    kb.register()
    logger.info("Registered a Knowledge Base in the basic example!")
    kb.unregister()
    logger.info("Unregistered the Knowledge Base in the basic example!")
