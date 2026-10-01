"""ASK interaction example.

Registers an ASK KI and executes it from this script to show how query bindings
and typed results work end-to-end.
"""

from rdflib import URIRef
from shared import get_example_logger

from knowledge_mapper import (
    AskExchangeInfo,
    BindingModel,
    KnowledgeBase,
    Literal,
    Uri,
)

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
    # ask_with_info() also returns the exchange info reported by the KE; use
    # kb.ask() if you only need the bindings. Passing binding_model types the
    # result as PersonBindings.
    result = await kb.ask_with_info(
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
        binding_model=PersonBinding,
    )
    logger.info(f"Received result from ASK KI: {result.binding_set}")
    for info in result.exchange_info:
        logger.info(
            f"Exchanged with {info.knowledge_base_id}: {info.status} "
            f"({info.exchange_end - info.exchange_start})"
        )
        if isinstance(info, AskExchangeInfo):
            logger.info(f"  answered with: {info.binding_set}")

    await kb.unregister()
    logger.info("KB unregistered.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
