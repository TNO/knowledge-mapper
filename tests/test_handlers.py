import pytest
from rdflib import URIRef

from src.ke.models import BindingModel, BindingSet, Uri
from src.knowledge_base import KnowledgeBase


@pytest.fixture
def kb():
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )

    return kb


def sensor_handler(binding_set, info):
    SENSORS = [
        URIRef("http://example.org/test#sensor1"),
        URIRef("http://example.org/test#sensor2"),
    ]
    if binding_set:
        filtered_sensors = [b["sensor"] for b in binding_set if b["sensor"] in SENSORS]
    else:
        filtered_sensors = SENSORS
    return [{"sensor": sensor} for sensor in filtered_sensors]


def test_handler_with_untyped_binding_set(kb: KnowledgeBase):
    @kb.answer_ki(
        name="test-untyped-answer-ki",
        graph_pattern="""
            ?sensor a ex:Sensor ;
            """,
        prefixes={"ex": "http://example.org/test#"},
    )
    def test_untyped_answer_ki(binding_set: BindingSet, info) -> BindingSet:
        SENSORS = [
            "<http://example.org/test#sensor1>",
            "<http://example.org/test#sensor2>",
        ]
        if binding_set:
            filtered_sensors = [
                binding["sensor"]
                for binding in binding_set
                if binding["sensor"] in SENSORS
            ]
        else:
            filtered_sensors = SENSORS
        return [{"sensor": sensor} for sensor in filtered_sensors]

    result = kb.call(
        [{"sensor": "<http://example.org/test#sensor1>"}], "test-untyped-answer-ki"
    )
    assert result == [
        {"sensor": "<http://example.org/test#sensor1>"},
    ]


def test_handler_with_typed_binding_set(kb: KnowledgeBase):
    class TestBinding(BindingModel):
        sensor: Uri

    @kb.answer_ki(
        name="typed-answer-ki",
        graph_pattern="""
            ?sensor a ex:Sensor ;
            """,
        prefixes={"ex": "http://example.org/test#"},
    )
    def test_answer_ki(binding_set: list[TestBinding], info) -> list[TestBinding]:
        SENSORS = [
            URIRef("http://example.org/test#sensor1"),
            URIRef("http://example.org/test#sensor2"),
        ]
        if binding_set:
            filtered_sensors = [
                binding.sensor for binding in binding_set if binding.sensor in SENSORS
            ]
        else:
            filtered_sensors = SENSORS
        return [TestBinding(sensor=sensor) for sensor in filtered_sensors]

    result = kb.call(
        [{"sensor": "<http://example.org/test#sensor1>"}], "typed-answer-ki"
    )
    assert result == [
        {"sensor": "<http://example.org/test#sensor1>"},
    ]
