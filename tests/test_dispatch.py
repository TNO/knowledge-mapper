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


async def test_dispatch_untyped_handler():
    """dispatch() with a raw-BindingSet handler passes through without conversion."""

    def handler(binding_set: BindingSet, info) -> BindingSet:
        return [{"sensor": b["sensor"]} for b in binding_set]

    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ANSWER, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=handler,
    )

    result = await ctx.dispatch([{"sensor": "<http://example.org/s1>"}])
    assert result == [{"sensor": "<http://example.org/s1>"}]


async def test_dispatch_typed_handler():
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
    result = await ctx.dispatch(raw_input)
    assert result == [{"sensor": "<http://example.org/s1>"}]


async def test_dispatch_react_typed():
    """dispatch() works for REACT KIs with typed handlers."""

    def handler(binding_set: list[MeasurementBinding], info) -> list[ResultBinding]:
        return [ResultBinding(measurement=b.measurement) for b in binding_set]

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
    result = await ctx.dispatch(raw)
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


# -- async handler dispatch ---------------------------------------------------


async def test_dispatch_async_handler():
    """dispatch() detects an async handler and awaits it directly."""

    async def handler(binding_set: BindingSet, info) -> BindingSet:
        return [{"sensor": b["sensor"]} for b in binding_set]

    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ANSWER, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=handler,
    )

    result = await ctx.dispatch([{"sensor": "<http://example.org/s1>"}])
    assert result == [{"sensor": "<http://example.org/s1>"}]


async def test_dispatch_sync_handler_runs_in_thread():
    """dispatch() runs a sync handler via asyncio.to_thread (off the event loop)."""
    import threading

    event_loop_thread = threading.current_thread()
    handler_thread = None

    def handler(binding_set: BindingSet, info) -> BindingSet:
        nonlocal handler_thread
        handler_thread = threading.current_thread()
        return binding_set

    ctx = KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            type=KiTypes.ANSWER, name="ki", prefixes={}, graph_pattern=GRAPH_PATTERN
        ),
        handler=handler,
    )

    await ctx.dispatch([{"sensor": "<http://example.org/s1>"}])
    assert handler_thread is not None
    assert handler_thread is not event_loop_thread


async def test_dispatch_async_handler_via_decorator():
    """Decorator-registered async handler is detected as async and awaited."""
    import threading

    from knowledge_mapper import KnowledgeBase

    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="test",
        ke_url="http://fake-ke",
    )

    event_loop_thread = threading.current_thread()
    handler_thread = None

    @kb.answer_ki(name="async-ki", graph_pattern=GRAPH_PATTERN)
    async def my_handler(binding_set: BindingSet, info) -> BindingSet:
        nonlocal handler_thread
        handler_thread = threading.current_thread()
        return binding_set

    result = await kb.call([{"sensor": "<http://example.org/s1>"}], "async-ki")
    assert result == [{"sensor": "<http://example.org/s1>"}]
    # Async handler runs on the event loop thread, not in a separate thread
    assert handler_thread is event_loop_thread
