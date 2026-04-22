import pytest

from src import KnowledgeBase
from src.ke.models import BindingModel

from .fake_client import FakeClient

@pytest.fixture
def client():
    return FakeClient(fake_url="http://fake-ke")

@pytest.fixture
def kb(client: FakeClient):
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )
    kb.client = client
    kb.register()
    return kb


def test_post_measurement_no_binding_models(kb: KnowledgeBase, client: FakeClient):
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
                ex:storedBy ?kb ;
        """,
        prefixes={"ex": "http://example.org/test#"},
        defer_ke_registration=False,
    )

    client.mock_result_binding_set(
        ki_name="post-ki",
        binding_set=[
            {
                "measurement": "http://example.org/test#measurement1",
                "kb": "http://example.org/test#kb",
            }
        ],
    )

    result = kb.post(
        [
            {
                "measurement": "http://example.org/test#measurement1",
                "value": "'42.0'^^xsd:float",
                "unit": "http://example.org/test#unit1",
                "time": "'2024-01-01T12:00:00Z'^^xsd:dateTime",
            }
        ],
        "post-ki",
    )

    assert result == [
        {
            "measurement": "http://example.org/test#measurement1",
            "kb": "http://example.org/test#kb",
        }
    ]

def test_post_measurement_with_binding_models(kb: KnowledgeBase, client: FakeClient):
    class MeasurementBinding(BindingModel):
        measurement: str
        value: float
        unit: str
        time: str

    class ResultBinding(BindingModel):
        measurement: str
        kb: str

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
                ex:storedBy ?kb ;
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
                "measurement": "http://example.org/test#measurement1",
                "kb": "http://example.org/test#kb",
            }
        ],
    )

    result = kb.post(
        [
            MeasurementBinding(
                measurement="http://example.org/test#measurement1",
                value=42.0,
                unit="http://example.org/test#unit1",
                time="2024-01-01T12:00:00Z",
            )
        ],
        "post-ki",
    )

    assert result == [
        ResultBinding(
            measurement="http://example.org/test#measurement1",
            kb="http://example.org/test#kb",
        )
    ]