"""Binding models example: compare typed vs raw binding handling.

This example registers two ANSWER KIs with the same pattern:
1. A typed handler using a BindingModel class.
2. A raw handler using plain BindingSet dictionaries.
"""

from datetime import datetime

from rdflib import URIRef
from shared import get_example_logger

from knowledge_mapper import (
    BindingModel,
    BindingSet,
    KnowledgeBase,
    KnowledgeInteractionInfo,
    Literal,
    Uri,
)

EXAMPLE_NAME = "binding-models"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/binding-models#kb",
    name="binding-models-kb",
    description="An example KB that demonstrates the use of binding models.",
    ke_url="http://localhost:8280/rest",
)


# Define strongly-typed bindings for variables in the graph pattern.
class CurrentTemperatureBinding(BindingModel):
    measurement: Uri
    value: Literal[float]
    unit: Uri
    time: Literal[datetime]


@kb.answer_ki(
    name="binding-models-answer-ki",
    graph_pattern="""
        ?measurement a ex:Measurement ;
            ex:hasValue ?value ;
            ex:hasUnit ?unit ;
            ex:hasTime ?time .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/binding-models#"},
)
def binding_models_answer_ki(
    binding_set: list[CurrentTemperatureBinding], info: KnowledgeInteractionInfo
) -> list[CurrentTemperatureBinding]:
    logger.info(
        f"Handling a call to the binding models answer KI with incoming bindings: "
        f"{binding_set}"
    )
    # Return a single current measurement using typed values.
    return [
        CurrentTemperatureBinding(
            measurement=URIRef(
                "http://example.org/knowledge-mapper/binding-models#currentTemp"
            ),
            value=22.5,
            unit=URIRef("http://example.org/knowledge-mapper/binding-models#Celsius"),
            time=datetime.now(),
        )
    ]


@kb.answer_ki(
    name="binding-models-raw-answer-ki",
    graph_pattern="""
        ?measurement a ex:Measurement ;
            ex:hasValue ?value ;
            ex:hasUnit ?unit ;
            ex:hasTime ?time .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/binding-models#"},
)
def binding_models_raw_answer_ki(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    logger.info(
        f"Handling a call to the binding models raw answer KI with incoming bindings: "
        f"{binding_set}"
    )
    # Return the same shape as above, but manually encoded as raw strings.
    return [
        {
            "measurement": "<http://example.org/knowledge-mapper/binding-models#currentTemp>",
            "value": "'22.5'^^xsd:float",
            "unit": "<http://example.org/knowledge-mapper/binding-models#Celsius>",
            "time": datetime.now().isoformat(),
        }
    ]


if __name__ == "__main__":
    # Register both KIs, then cleanly unregister.
    kb.connect()
    kb.register()
    logger.info("Registered the binding models example KB!")

    kb.unregister()
    logger.info("Unregistered the binding models example KB!")
