import sys
from pathlib import Path
from typing import cast

from rdflib import URIRef

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared import get_example_logger

from knowledge_mapper import BindingModel, KnowledgeBase, Literal, Uri

EXAMPLE_NAME = "testing"
logger = get_example_logger(EXAMPLE_NAME)

kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/testing#kb",
    name="testing-kb",
    description="An example KB that demonstrates testing the KB.",
    ke_url="http://localhost:8280/rest",
)

kb.ask_ki(
    name="ask-ki-no-binding-model",
    graph_pattern="""
        ?s a ex:TestSubject ;
            ex:hasValue ?value .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/testing#"},
)


class ExampleBinding(BindingModel):
    s: Uri
    value: Literal[str]


kb.ask_ki(
    name="ask-ki-with-binding-model",
    graph_pattern="""
        ?s a ex:TestSubject ;
            ex:hasValue ?value .
    """,
    binding_model=ExampleBinding,
    prefixes={"ex": "http://example.org/knowledge-mapper/testing#"},
)


async def ask_for_values_of_subject(subject_name: str) -> list[str]:
    result_binding_set: list[ExampleBinding] = await kb.ask(
        [
            ExampleBinding(
                s=URIRef(f"http://example.org/knowledge-mapper/testing#{subject_name}"),
                value=None,
            )
        ],
        "ask-ki-with-binding-model",
    )  # pyright: ignore[reportAssignmentType]
    return (
        [str(binding.value) for binding in result_binding_set]
        if result_binding_set
        else []
    )


class ResultBinding(BindingModel):
    s: Uri
    other: Uri


kb.post_ki(
    name="post-ki",
    argument_graph_pattern="""
        ?s a ex:TestSubject ;
            ex:hasValue ?value .
    """,
    result_graph_pattern="""
        ?s a ex:TestSubject ;
            ex:storedBy ?other .
    """,
    argument_binding_model=ExampleBinding,
    result_binding_model=ResultBinding,
    prefixes={"ex": "http://example.org/knowledge-mapper/testing#"},
)


async def repeat_value_post(value: str, iterations: int) -> list[URIRef]:
    result_binding_set: list[ResultBinding] = []
    for i in range(iterations):
        result_binding_set.extend(
            await kb.post(
                [
                    ExampleBinding(
                        s=URIRef(
                            f"http://example.org/knowledge-mapper/testing#Subject-{i}"
                        ),
                        value=value,
                    )
                ],
                "post-ki",
            )  # type: ignore
        )
    return [cast(URIRef, binding.other) for binding in result_binding_set]


if __name__ == "__main__":
    logger.info(
        "This KB demonstrates testing, and is not meant to be run as a standalone "
        "example."
    )
