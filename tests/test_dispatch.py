"""Tests for dispatch/prepare_outgoing/parse_result on KnowledgeInteractionContext."""

from rdflib import URIRef

from knowledge_mapper.ke.models import (
    AskAnswerInteractionInfo,
    BindingModel,
    BindingSet,
    KiTypes,
    Literal,
    PostReactInteractionInfo,
    Uri,
)
from knowledge_mapper.knowledge_interaction import KnowledgeInteractionContext

GRAPH_PATTERN = "?s ?p ?o ."


class SensorBinding(BindingModel):
    sensor: Uri


class MeasurementBinding(BindingModel):
    measurement: Uri
    value: Literal[float]


class ResultBinding(BindingModel):
    measurement: Uri


# -- dispatch (ANSWER/REACT) -------------------------------------------------


def test_dispatch_untyped_handler():
    """dispatch() with a raw-BindingSet handler passes through without conversion."""

    def handler(binding_set: BindingSet, info) -> BindingSet:
        return [{"sensor": b["sensor"]} for b in binding_set]

    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ANSWER, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=handler,
    )

    result = ctx.dispatch([{"sensor": "<http://example.org/s1>"}])
    assert result == [{"sensor": "<http://example.org/s1>"}]


def test_dispatch_typed_handler():
    """dispatch() validates incoming bindings and serializes outgoing ones."""

    def handler(binding_set: list[SensorBinding], info) -> list[SensorBinding]:
        return binding_set

    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ANSWER, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=handler,
    )

    raw_input = [{"sensor": "<http://example.org/s1>"}]
    result = ctx.dispatch(raw_input)
    assert result == [{"sensor": "<http://example.org/s1>"}]


def test_dispatch_react_typed():
    """dispatch() works for REACT KIs with typed handlers."""

    def handler(
        binding_set: list[MeasurementBinding], info
    ) -> list[ResultBinding]:
        return [
            ResultBinding(measurement=b.measurement) for b in binding_set
        ]

    ctx = KnowledgeInteractionContext(
        info=PostReactInteractionInfo(
            type=KiTypes.REACT,
            name="ki",
            prefixes={},
            argument_graph_pattern=GRAPH_PATTERN,
            result_graph_pattern=GRAPH_PATTERN,
        ),
        handler=handler,
    )

    raw = [
        {
            "measurement": "<http://example.org/m1>",
            "value": '"42.0"^^<http://www.w3.org/2001/XMLSchema#float>',
        }
    ]
    result = ctx.dispatch(raw)
    assert result == [{"measurement": "<http://example.org/m1>"}]


# -- prepare_outgoing (ASK/POST) ----------------------------------------------


def test_prepare_outgoing_no_model():
    """Without a serialization model, bindings pass through untouched."""
    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ASK, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=None,
    )

    raw = [{"sensor": "<http://example.org/s1>"}]
    assert ctx.prepare_outgoing(raw) is raw


def test_prepare_outgoing_with_model():
    """With a serialization model, BindingModels are dumped to raw dicts."""
    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ASK, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=None,
        serialization_model=SensorBinding,
    )

    models = [SensorBinding(sensor=URIRef("http://example.org/s1"))]
    result = ctx.prepare_outgoing(models)
    assert result == [{"sensor": "<http://example.org/s1>"}]


# -- parse_result (ASK/POST) --------------------------------------------------


def test_parse_result_no_model():
    """Without a validation model, bindings pass through untouched."""
    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ASK, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=None,
    )

    raw = [{"sensor": "<http://example.org/s1>"}]
    assert ctx.parse_result(raw) is raw


def test_parse_result_with_model():
    """With a validation model, raw dicts are validated into BindingModels."""
    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ASK, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=None,
        validation_model=SensorBinding,
    )

    raw = [{"sensor": "<http://example.org/s1>"}]
    result = ctx.parse_result(raw)
    assert result == [SensorBinding(sensor=URIRef("http://example.org/s1"))]


def test_parse_result_empty_binding_set():
    """parse_result with an empty binding set returns it as-is."""
    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ASK, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=None,
        validation_model=SensorBinding,
    )

    assert ctx.parse_result([]) == []
