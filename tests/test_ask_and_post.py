import pytest
from rdflib import URIRef

from src.knowledge_mapper import KnowledgeBase
from src.knowledge_mapper.ke.models import BindingModel, Literal, Uri
from src.knowledge_mapper.ke.testing import TestClient


@pytest.fixture
def client():
    return TestClient(fake_url="http://fake-ke")


@pytest.fixture
def kb(client: TestClient):
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )
    kb.client = client
    kb.register()
    return kb


def test_ask_interaction_no_binding_models(kb: KnowledgeBase, client: TestClient):
    kb.ask_ki(
        name="ask-ki",
        graph_pattern="""
            ?person a ex:Person ;
                ex:hasName ?name ;
                ex:hasAge ?age .
        """,
        prefixes={"ex": "http://example.org/test#"},
        defer_ke_registration=False,
    )

    client.mock_result_binding_set(
        ki_name="ask-ki",
        binding_set=[
            {
                "person": "http://example.org/test#person1",
                "name": "'Alice'^^xsd:string",
                "age": "'30'^^xsd:integer",
            }
        ],
    )

    result = kb.ask(
        [
            {
                "person": "http://example.org/test#person1",
            }
        ],
        "ask-ki",
    )

    assert result == [
        {
            "person": "http://example.org/test#person1",
            "name": "'Alice'^^xsd:string",
            "age": "'30'^^xsd:integer",
        }
    ]


def test_ask_interaction_with_binding_models(kb: KnowledgeBase, client: TestClient):
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
        prefixes={"ex": "http://example.org/test#"},
        defer_ke_registration=False,
    )

    client.mock_result_binding_set(
        ki_name="ask-ki",
        binding_set=[
            {
                "person": "<http://example.org/test#person1>",
                "name": '"Alice"^^xsd:string',
                "age": '"30"^^xsd:integer',
            }
        ],
    )

    result = kb.ask(
        [
            PersonBinding(
                person=URIRef("http://example.org/test#person1"),
                name=None,
                age=None,
            )
        ],
        "ask-ki",
    )

    assert result == [
        PersonBinding(
            person=URIRef("http://example.org/test#person1"),
            name="Alice",
            age=30,
        )
    ]


def test_post_measurement_no_binding_models(kb: KnowledgeBase, client: TestClient):
    kb.post_ki(
        name="post-ki",
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
        prefixes={"ex": "http://example.org/test#"},
        defer_ke_registration=False,
    )

    client.mock_result_binding_set(
        ki_name="post-ki",
        binding_set=[
            {
                "measurement": "<http://example.org/test#measurement1>",
                "kb": "<http://example.org/test#kb>",
            }
        ],
    )

    result = kb.post(
        [
            {
                "measurement": "<http://example.org/test#measurement1>",
                "value": "'42.0'^^xsd:float",
                "unit": "<http://example.org/test#unit1>",
                "time": "'2024-01-01T12:00:00Z'^^xsd:dateTime",
            }
        ],
        "post-ki",
    )

    assert result == [
        {
            "measurement": "<http://example.org/test#measurement1>",
            "kb": "<http://example.org/test#kb>",
        }
    ]


def test_post_measurement_with_binding_models(kb: KnowledgeBase, client: TestClient):
    class MeasurementBinding(BindingModel):
        measurement: Uri
        value: Literal[float]
        unit: Uri
        time: Literal[str]

    class ResultBinding(BindingModel):
        measurement: Uri
        kb: Uri

    kb.post_ki(
        name="post-ki",
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
        prefixes={"ex": "http://example.org/test#"},
        argument_binding_model=MeasurementBinding,
        result_binding_model=ResultBinding,
        defer_ke_registration=False,
    )

    client.mock_result_binding_set(
        ki_name="post-ki",
        binding_set=[
            {
                "measurement": "<http://example.org/test#measurement1>",
                "kb": "<http://example.org/test#kb>",
            }
        ],
    )

    result = kb.post(
        [
            MeasurementBinding(
                measurement=URIRef("http://example.org/test#measurement1"),
                value=42.0,
                unit=URIRef("http://example.org/test#unit1"),
                time="2024-01-01T12:00:00Z",
            )
        ],
        "post-ki",
    )

    assert result == [
        ResultBinding(
            measurement=URIRef("http://example.org/test#measurement1"),
            kb=URIRef("http://example.org/test#kb"),
        )
    ]
