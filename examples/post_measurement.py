import time
from datetime import datetime
from uuid import uuid4

from rdflib import URIRef
from shared import get_example_logger

from src.knowledge_mapper.kb.knowledge_base import KnowledgeBase
from src.knowledge_mapper.ke.models import (
    BindingModel,
    Literal,
    Uri,
)

EXAMPLE_NAME = "post-measurement"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/post-measurement#kb",
    name="post-measurement-kb",
    description="An example KB that demonstrates handling a POST KI for posting a new "
    "measurement.",
    ke_url="http://localhost:8280/rest",
)


class MeasurementBinding(BindingModel):
    measurement: Uri
    value: Literal[float]
    unit: Uri
    time: Literal[datetime]


class ResultBinding(BindingModel):
    measurement: Uri
    kb: Uri


kb.post_ki(
    name="post-measurement-ki",
    argument_graph_pattern="""
        ?measurement a ex:Measurement ;
            ex:hasValue ?value ;
            ex:hasUnit ?unit ;
            ex:hasTime ?time .
    """,
    result_graph_pattern="""
        ?measurement a ex:Measurement ;
            ex:storedBy ?kb .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/post-measurement#"},
    result_binding_model=ResultBinding,
    argument_binding_model=MeasurementBinding,
)


if __name__ == "__main__":
    kb.register()
    logger.info("KB registered.")
    time.sleep(
        5
    )  # Sleep for a bit to allow time for testing the POST KI with an external client
    logger.info("Posting...")
    result_bindings = kb.post(
        [
            MeasurementBinding(
                measurement=URIRef(
                    f"http://example.org/knowledge-mapper/post-measurement#measurement-{uuid4()}"
                ),
                value=99.9,
                unit=URIRef(
                    "http://example.org/knowledge-mapper/post-measurement#Percent"
                ),
                time=datetime.now(),
            )
        ],
        "post-measurement-ki",
    )
    logger.info(f"Received result bindings: {result_bindings}")
    kb.unregister()
    logger.info("KB unregistered.")
