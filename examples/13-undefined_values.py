"""Undefined values example: bindings where some variables have no value.

The Knowledge Engine does not support optional values in a binding: every
variable in the graph pattern must be bound. When your data has no value for a
variable, assign a sentinel instead of `None`:
- `UNDEFINED` for `Uri` fields;
- `UNDEFINED_LITERAL` for `Literal[T]`, `RdfLiteral` and `Datatype` fields.

Both are sent as the URI <http://www.knowledge-engine.eu/mapper/undefined>.
Incoming bindings carrying that URI are deserialized back to the sentinel that
matches the field type, so check for it with `value is UNDEFINED` or
`value is UNDEFINED_LITERAL`. Type checkers such as pyright narrow the field
type on the latter check.
"""

from rdflib import Namespace
from shared import get_example_logger

from knowledge_mapper import (
    UNDEFINED,
    UNDEFINED_LITERAL,
    BindingModel,
    KnowledgeBase,
    KnowledgeInteraction,
    Literal,
    Uri,
)

EXAMPLE_NAME = "undefined-values"
logger = get_example_logger(EXAMPLE_NAME)

EX = Namespace("http://example.org/knowledge-mapper/undefined-values#")

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/undefined-values#kb",
    name="undefined-values-kb",
    description="An example KB that answers with partially unknown data.",
    ke_url="http://localhost:8280/rest",
)


class PersonBinding(BindingModel):
    person: Uri
    name: Literal[str]
    age: Literal[int]
    employer: Uri


# Ages and employers are not known for everyone.
PEOPLE = [
    PersonBinding(person=EX.alice, name="Alice", age=34, employer=EX.tno),
    PersonBinding(person=EX.bob, name="Bob", age=UNDEFINED_LITERAL, employer=EX.tno),
    PersonBinding(person=EX.carol, name="Carol", age=51, employer=UNDEFINED),
]


@kb.answer_ki(
    name="undefined-values-answer-ki",
    graph_pattern="""
        ?person a ex:Person ;
            ex:hasName ?name ;
            ex:hasAge ?age ;
            ex:worksFor ?employer .
    """,
    prefixes={"ex": str(EX)},
)
def people_answer_ki(
    binding_set: list[PersonBinding], info: KnowledgeInteraction
) -> list[PersonBinding]:
    logger.info(f"Handling a call to the people answer KI with: {binding_set}")
    # An asker may itself bind a variable to UNDEFINED, e.g. to ask for people
    # whose age is unknown.
    if any(binding.age is UNDEFINED_LITERAL for binding in binding_set):
        return [person for person in PEOPLE if person.age is UNDEFINED_LITERAL]
    return PEOPLE


async def main():
    # Register the KI, then cleanly unregister.
    await kb.connect()
    await kb.register()
    logger.info("Registered the undefined values example KB!")

    for person in PEOPLE:
        # Dumps fine: the sentinels count as values, unlike None.
        logger.info(person.dump_result_binding())

    await kb.unregister()
    logger.info("Unregistered the undefined values example KB!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
