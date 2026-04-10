from datetime import datetime

from rdflib import URIRef
from shared import get_example_logger

from src.ke.models import (
    BindingModel,
    BindingSet,
    KnowledgeInteractionInfo,
    Literal,
    Uri,
)
from src.knowledge_base import KnowledgeBase

EXAMPLE_NAME = "binding-models"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/binding-models#kb",
    name="binding-models-kb",
    description="An example KB that demonstrates the use of binding models.",
    ke_url="http://localhost:8280/rest",
)


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
    return [
        CurrentTemperatureBinding(
            measurement=URIRef("http://example.org/knowledge-mapper/binding-models#currentTemp"),
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
    return [
        {
            "measurement": "<http://example.org/knowledge-mapper/binding-models#currentTemp>",
            "value": 22.5,
            "unit": "<http://example.org/knowledge-mapper/binding-models#Celsius>",
            "time": datetime.now().isoformat(),
        }
    ]


if __name__ == "__main__":
    kb.connect()
    kb.register()
    logger.info("Registered the binding models example KB!")

    kb.unregister()
    logger.info("Unregistered the binding models example KB!")
