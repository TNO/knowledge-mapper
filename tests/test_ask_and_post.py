import pytest
from rdflib import URIRef

from knowledge_mapper import ExchangeInfo, ExchangeResult, KnowledgeBase
from knowledge_mapper.ke.models import BindingModel, Literal, Uri
from knowledge_mapper.testing import TestClient


@pytest.fixture
def client():
    return TestClient(fake_url="http://fake-ke")


@pytest.fixture
async def kb(client: TestClient):
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )
    kb.client = client
    await kb.register()
    return kb


async def test_ask_interaction_no_binding_models(kb: KnowledgeBase, client: TestClient):
    kb.ask_ki(
        name="ask-ki",
        graph_pattern="""
            ?person a ex:Person ;
                ex:hasName ?name ;
                ex:hasAge ?age .
        """,
        prefixes={"ex": "http://example.org/test#"},
    )
    await kb.sync_knowledge_interactions()

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

    result = await kb.ask(
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


async def test_ask_interaction_with_binding_models(
    kb: KnowledgeBase, client: TestClient
):
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
    )
    await kb.sync_knowledge_interactions()

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

    result = await kb.ask(
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


async def test_post_measurement_no_binding_models(
    kb: KnowledgeBase, client: TestClient
):
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
    )
    await kb.sync_knowledge_interactions()

    client.mock_result_binding_set(
        ki_name="post-ki",
        binding_set=[
            {
                "measurement": "<http://example.org/test#measurement1>",
                "kb": "<http://example.org/test#kb>",
            }
        ],
    )

    result = await kb.post(
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


async def test_post_measurement_with_binding_models(
    kb: KnowledgeBase, client: TestClient
):
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
    )
    await kb.sync_knowledge_interactions()

    client.mock_result_binding_set(
        ki_name="post-ki",
        binding_set=[
            {
                "measurement": "<http://example.org/test#measurement1>",
                "kb": "<http://example.org/test#kb>",
            }
        ],
    )

    result = await kb.post(
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


# ---------------------------------------------------------------------------
# ask_with_info / post_with_info: bindings plus exchange info
# ---------------------------------------------------------------------------


class PersonBinding(BindingModel):
    person: Uri
    name: Literal[str]


async def test_ask_with_info_returns_bindings_and_exchange_info(
    kb: KnowledgeBase, client: TestClient
):
    kb.ask_ki(
        name="ask-info-ki",
        graph_pattern="?person ex:hasName ?name .",
        prefixes={"ex": "http://example.org/test#"},
        binding_model=PersonBinding,
    )
    await kb.sync_knowledge_interactions()
    client.mock_result_binding_set(
        ki_name="ask-info-ki",
        binding_set=[
            {"person": "<http://example.org/test#p1>", "name": '"Alice"^^xsd:string'}
        ],
    )

    result = await kb.ask_with_info([], "ask-info-ki")

    assert isinstance(result, ExchangeResult)
    assert result.binding_set == [
        PersonBinding(person=URIRef("http://example.org/test#p1"), name="Alice")
    ]
    assert len(result.exchange_info) == 1
    info = result.exchange_info[0]
    assert isinstance(info, ExchangeInfo)
    assert info.knowledge_interaction_id == kb.ki_registry["ask-info-ki"].ke_id
    assert info.status == "OK"


async def test_post_with_info_returns_bindings_and_exchange_info(
    kb: KnowledgeBase, client: TestClient
):
    kb.post_ki(
        name="post-info-ki",
        argument_graph_pattern="?person ex:hasName ?name .",
        result_graph_pattern="?person ex:hasName ?name .",
        prefixes={"ex": "http://example.org/test#"},
        argument_binding_model=PersonBinding,
        result_binding_model=PersonBinding,
    )
    await kb.sync_knowledge_interactions()
    client.mock_result_binding_set(
        ki_name="post-info-ki",
        binding_set=[
            {"person": "<http://example.org/test#p1>", "name": '"Bob"^^xsd:string'}
        ],
    )

    result = await kb.post_with_info(
        [PersonBinding(person=URIRef("http://example.org/test#p1"), name="Bob")],
        "post-info-ki",
    )

    assert isinstance(result, ExchangeResult)
    assert result.binding_set == [
        PersonBinding(person=URIRef("http://example.org/test#p1"), name="Bob")
    ]
    assert len(result.exchange_info) == 1
    info = result.exchange_info[0]
    assert info.knowledge_interaction_id == kb.ki_registry["post-info-ki"].ke_id
    assert info.status == "OK"


async def test_ask_with_info_rejects_non_ask_ki(kb: KnowledgeBase):
    kb.post_ki(
        name="not-an-ask",
        argument_graph_pattern="?s ?p ?o .",
        result_graph_pattern="?s ?p ?o .",
    )
    await kb.sync_knowledge_interactions()

    with pytest.raises(ValueError, match="not ASK"):
        await kb.ask_with_info([], "not-an-ask")


# ---------------------------------------------------------------------------
# binding_model / result_binding_model keyword: typed results
# ---------------------------------------------------------------------------


class StoredByBinding(BindingModel):
    person: Uri
    kb: Uri


async def test_ask_with_binding_model_returns_parsed_bindings(
    kb: KnowledgeBase, client: TestClient
):
    kb.ask_ki(
        name="ask-typed-ki",
        graph_pattern="?person ex:hasName ?name .",
        prefixes={"ex": "http://example.org/test#"},
        binding_model=PersonBinding,
    )
    await kb.sync_knowledge_interactions()
    client.mock_result_binding_set(
        ki_name="ask-typed-ki",
        binding_set=[
            {"person": "<http://example.org/test#p1>", "name": '"Alice"^^xsd:string'}
        ],
    )

    result = await kb.ask([], "ask-typed-ki", binding_model=PersonBinding)
    with_info = await kb.ask_with_info([], "ask-typed-ki", binding_model=PersonBinding)

    expected = [
        PersonBinding(person=URIRef("http://example.org/test#p1"), name="Alice")
    ]
    assert result == expected
    assert with_info.binding_set == expected


async def test_post_with_result_binding_model_returns_parsed_bindings(
    kb: KnowledgeBase, client: TestClient
):
    kb.post_ki(
        name="post-typed-ki",
        argument_graph_pattern="?person ex:hasName ?name .",
        result_graph_pattern="?person ex:storedBy ?kb .",
        prefixes={"ex": "http://example.org/test#"},
        argument_binding_model=PersonBinding,
        result_binding_model=StoredByBinding,
    )
    await kb.sync_knowledge_interactions()
    client.mock_result_binding_set(
        ki_name="post-typed-ki",
        binding_set=[
            {
                "person": "<http://example.org/test#p1>",
                "kb": "<http://example.org/test#kb>",
            }
        ],
    )

    result = await kb.post(
        [PersonBinding(person=URIRef("http://example.org/test#p1"), name="Bob")],
        "post-typed-ki",
        result_binding_model=StoredByBinding,
    )

    assert result == [
        StoredByBinding(
            person=URIRef("http://example.org/test#p1"),
            kb=URIRef("http://example.org/test#kb"),
        )
    ]


async def test_ask_rejects_binding_model_not_registered_for_ki(kb: KnowledgeBase):
    kb.ask_ki(
        name="ask-typed-ki",
        graph_pattern="?person ex:hasName ?name .",
        prefixes={"ex": "http://example.org/test#"},
        binding_model=PersonBinding,
    )
    kb.ask_ki(name="ask-raw-ki", graph_pattern="?s ?p ?o .")
    await kb.sync_knowledge_interactions()

    with pytest.raises(ValueError, match="does not match"):
        await kb.ask([], "ask-typed-ki", binding_model=StoredByBinding)
    with pytest.raises(ValueError, match="does not match"):
        await kb.ask([], "ask-raw-ki", binding_model=PersonBinding)


async def test_post_rejects_result_binding_model_not_registered_for_ki(
    kb: KnowledgeBase,
):
    kb.post_ki(
        name="post-typed-ki",
        argument_graph_pattern="?person ex:hasName ?name .",
        result_graph_pattern="?person ex:storedBy ?kb .",
        prefixes={"ex": "http://example.org/test#"},
        argument_binding_model=PersonBinding,
        result_binding_model=StoredByBinding,
    )
    await kb.sync_knowledge_interactions()

    # The argument model is not the result model.
    with pytest.raises(ValueError, match="does not match"):
        await kb.post([], "post-typed-ki", result_binding_model=PersonBinding)
