"""ASK interaction example.

Registers an ASK KI and executes it from this script to show how query bindings
and typed results work end-to-end.
"""

from rdflib import URIRef
from shared import get_example_logger

from knowledge_mapper import BindingModel, KnowledgeBase, Literal, Uri

EXAMPLE_NAME = "ask-interaction"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/ask-interaction#kb",
    name="ask-interaction-kb",
    description="An example KB that demonstrates handling an ASK KI.",
    ke_url="http://localhost:8280/rest",
)


# Binding model for variables used in the ASK graph pattern.
class PersonBinding(BindingModel):
    person: Uri
    name: Literal[str]
    age: Literal[int]


# Register an ASK KI that can be called via kb.ask(...).
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


async def main():
    # Register this KB, execute one ASK request, and then unregister.
    await kb.register()
    logger.info("KB registered.")
    result = await kb.ask(
        [
            PersonBinding(
                person=URIRef(
                    "http://example.org/knowledge-mapper/ask-interaction#person1"
                ),
                name=None,
                age=None,
            )
        ],
        "ask-ki",
    )
    logger.info(f"Received result from ASK KI: {result}")

    await kb.unregister()
    logger.info("KB unregistered.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
