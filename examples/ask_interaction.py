from shared import get_example_logger

from src import KnowledgeBase
from src.ke.models import BindingModel, Literal, Uri

EXAMPLE_NAME = "ask-interaction"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/ask-interaction#kb",
    name="ask-interaction-kb",
    description="An example KB that demonstrates handling an ASK KI.",
    ke_url="http://localhost:8280/rest",
)


class PersonBinding(BindingModel):
    person: Uri
    name: Literal[str]
    age: Literal[int]


kb.ask_ki(
    name="ask-ki",
    graph_pattern="""
        ?person a ex:Person ;
            ex:hasName ?name ;
            ex:hasAge ?age .
    """,
    binding_model=PersonBinding,
    prefixes={"ex": "http://example.org/knowledge-mapper/ask-interaction#"},
)

if __name__ == "__main__":
    kb.register()
    logger.info("KB registered.")
    result = kb.ask(
        [
            {
                "person": "http://example.org/knowledge-mapper/ask-interaction#person1",
            }
        ],
        "ask-ki",
    )
    logger.info(f"Received result from ASK KI: {result}")

    kb.unregister()
    logger.info("KB unregistered.")