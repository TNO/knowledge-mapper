"""Custom datatypes example: literals with non-XSD datatypes in binding models.

By default, `Literal[T]` infers an XSD datatype from the Python value. This
example shows two ways to work with custom (non-XSD) datatypes instead:
1. `Annotated[Literal[T], Datatype(...)]` fixes the datatype of a field while
   keeping a plain Python value in your code.
2. `RdfLiteral` keeps the `rdflib.Literal` as-is, preserving any datatype or
   language tag.
"""

from datetime import datetime
from typing import Annotated

from rdflib import Literal as RDFLiteral
from rdflib import Namespace, URIRef
from shared import get_example_logger

from knowledge_mapper import (
    BindingModel,
    Datatype,
    KnowledgeBase,
    KnowledgeInteraction,
    Literal,
    RdfLiteral,
    Uri,
)

EXAMPLE_NAME = "custom-datatypes"
logger = get_example_logger(EXAMPLE_NAME)

EX = Namespace("http://example.org/knowledge-mapper/custom-datatypes#")

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/custom-datatypes#kb",
    name="custom-datatypes-kb",
    description="An example KB that demonstrates custom literal datatypes.",
    ke_url="http://localhost:8280/rest",
)


class ObservationBinding(BindingModel):
    observation: Uri
    timestamp: Literal[datetime]
    # Python float in code, serialized as "..."^^ex:celsius. Incoming literals
    # with any other datatype are rejected.
    temperature: Annotated[Literal[float], Datatype(EX.celsius)]
    # Raw rdflib Literal: any datatype or language tag is passed through.
    remark: RdfLiteral


@kb.answer_ki(
    name="custom-datatypes-answer-ki",
    graph_pattern="""
        ?observation a ex:Observation ;
            ex:hasTimestamp ?timestamp ;
            ex:hasTemperature ?temperature ;
            ex:hasRemark ?remark .
    """,
    prefixes={"ex": str(EX)},
)
def custom_datatypes_answer_ki(
    binding_set: list[ObservationBinding], info: KnowledgeInteraction
) -> list[ObservationBinding]:
    logger.info(
        f"Handling a call to the custom datatypes answer KI with incoming bindings: "
        f"{binding_set}"
    )
    return [
        ObservationBinding(
            observation=URIRef(EX.observation1),
            timestamp=datetime.now(),
            temperature=21.5,
            remark=RDFLiteral("sunny", datatype=EX.weatherCode),
        )
    ]


async def main():
    # Register the KI, then cleanly unregister.
    await kb.connect()
    await kb.register()
    logger.info("Registered the custom datatypes example KB!")

    await kb.unregister()
    logger.info("Unregistered the custom datatypes example KB!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
