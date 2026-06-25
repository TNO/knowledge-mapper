"""Tests for the handling loop using TestClient's enqueue methods."""

import asyncio
import time

import pytest

from knowledge_mapper import KnowledgeBase
from knowledge_mapper.ke.models import (
    BindingSet,
    KnowledgeInteraction,
)
from knowledge_mapper.testing import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(fake_url="http://fake-ke")


@pytest.fixture
async def kb(client: TestClient) -> KnowledgeBase:
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing the handling loop.",
        ke_url="http://fake-ke",
    )
    kb.client = client

    captured: list[BindingSet] = []

    @kb.answer_ki(
        name="echo-ki",
        graph_pattern="?s ?p ?o .",
    )
    def echo_handler(binding_set: BindingSet, info: KnowledgeInteraction) -> BindingSet:
        captured.append(binding_set)
        return binding_set

    await kb.register()
    kb._test_captured = captured  # type: ignore[attr-defined]
    return kb


async def test_handle_dispatches_to_handler(kb: KnowledgeBase, client: TestClient):
    """Enqueueing a HANDLE request dispatches to the handler and posts a response."""
    input_bs: BindingSet = [{"s": "ex:A", "p": "ex:rel", "o": "ex:B"}]
    client.enqueue_handle_request("echo-ki", input_bs)

    await kb.start_handling_loop(loops=1)

    assert kb._test_captured == [input_bs]  # type: ignore[attr-defined]
    assert client.last_handle_response == input_bs


async def test_exit_stops_loop(kb: KnowledgeBase, client: TestClient):
    """An EXIT signal terminates the loop without requiring a loops limit."""
    client.enqueue_exit()
    await kb.start_handling_loop()  # would hang without the EXIT signal


async def test_handle_then_exit(kb: KnowledgeBase, client: TestClient):
    """A HANDLE followed by EXIT processes the request and then stops."""
    input_bs: BindingSet = [{"s": "ex:X"}]
    client.enqueue_handle_request("echo-ki", input_bs)
    client.enqueue_exit()

    await kb.start_handling_loop()

    assert kb._test_captured == [input_bs]  # type: ignore[attr-defined]
    assert client.last_handle_response == input_bs


async def test_multiple_handle_requests(kb: KnowledgeBase, client: TestClient):
    """Multiple HANDLE requests are processed in order."""
    bs1: BindingSet = [{"s": "ex:1"}]
    bs2: BindingSet = [{"s": "ex:2"}]
    client.enqueue_handle_request("echo-ki", bs1)
    client.enqueue_handle_request("echo-ki", bs2)
    client.enqueue_exit()

    await kb.start_handling_loop()

    assert kb._test_captured == [bs1, bs2]  # type: ignore[attr-defined]
    assert len(client._handle_responses) == 2
    assert client._handle_responses[0][3] == bs1
    assert client._handle_responses[1][3] == bs2


def test_enqueue_unknown_ki_raises(client: TestClient):
    """Enqueueing a handle request for an unregistered KI raises KeyError."""
    with pytest.raises(KeyError, match="No registered KI named 'nonexistent'"):
        client.enqueue_handle_request("nonexistent", [])


# -- Concurrent handling loop tests ------------------------------------------


async def test_concurrent_dispatch_overlaps_in_time(client: TestClient):
    """Two slow handlers run concurrently — total wall time is less than 2x."""
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="test",
        ke_url="http://fake-ke",
    )
    kb.client = client

    handler_entries: list[float] = []
    handler_exits: list[float] = []

    @kb.answer_ki(name="slow-ki", graph_pattern="?s ?p ?o .")
    async def slow_handler(
        binding_set: BindingSet, info: KnowledgeInteraction
    ) -> BindingSet:
        handler_entries.append(time.monotonic())
        await asyncio.sleep(0.1)
        handler_exits.append(time.monotonic())
        return binding_set

    await kb.register()

    client.enqueue_handle_request("slow-ki", [{"s": "ex:1"}])
    client.enqueue_handle_request("slow-ki", [{"s": "ex:2"}])
    client.enqueue_exit()

    t0 = time.monotonic()
    await kb.start_handling_loop()
    elapsed = time.monotonic() - t0

    assert len(handler_entries) == 2
    assert len(handler_exits) == 2
    # If sequential, elapsed >= 0.2s. Concurrent should be ~0.1s.
    assert elapsed < 0.18, f"Handlers ran sequentially (elapsed={elapsed:.3f}s)"
    # Second handler started before first handler finished
    assert handler_entries[1] < handler_exits[0], "Handlers did not overlap"


async def test_handler_exception_posts_empty_binding_set(client: TestClient):
    """When a handler raises, an empty binding set is posted and the loop continues."""
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="test",
        ke_url="http://fake-ke",
    )
    kb.client = client

    @kb.answer_ki(name="boom-ki", graph_pattern="?s ?p ?o .")
    async def boom_handler(
        binding_set: BindingSet, info: KnowledgeInteraction
    ) -> BindingSet:
        raise RuntimeError("handler exploded")

    @kb.answer_ki(name="ok-ki", graph_pattern="?s ?p ?o .")
    async def ok_handler(
        binding_set: BindingSet, info: KnowledgeInteraction
    ) -> BindingSet:
        return binding_set

    await kb.register()

    client.enqueue_handle_request("boom-ki", [{"s": "ex:bad"}])
    client.enqueue_handle_request("ok-ki", [{"s": "ex:good"}])
    client.enqueue_exit()

    await kb.start_handling_loop()

    assert len(client._handle_responses) == 2
    # First response is the error — empty binding set
    assert client._handle_responses[0][3] == []
    # Second response is the success
    assert client._handle_responses[1][3] == [{"s": "ex:good"}]


async def test_exit_awaits_in_flight_handlers(client: TestClient):
    """On EXIT, the loop waits for in-flight handlers to finish before returning."""
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="test",
        ke_url="http://fake-ke",
    )
    kb.client = client

    handler_completed = False

    @kb.answer_ki(name="slow-ki", graph_pattern="?s ?p ?o .")
    async def slow_handler(
        binding_set: BindingSet, info: KnowledgeInteraction
    ) -> BindingSet:
        nonlocal handler_completed
        await asyncio.sleep(0.1)
        handler_completed = True
        return binding_set

    await kb.register()

    # Handler starts, then EXIT arrives while handler is still running
    client.enqueue_handle_request("slow-ki", [{"s": "ex:1"}])
    client.enqueue_exit()

    await kb.start_handling_loop()

    # The loop should have waited for the handler to complete
    assert handler_completed, "Loop returned before in-flight handler finished"
    assert len(client._handle_responses) == 1


async def test_semaphore_bounds_concurrency(client: TestClient):
    """No more than max_concurrent_handlers run at the same time."""
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="test",
        ke_url="http://fake-ke",
    )
    kb.client = client

    max_observed = 0
    current = 0
    lock = asyncio.Lock()

    @kb.answer_ki(name="counting-ki", graph_pattern="?s ?p ?o .")
    async def counting_handler(
        binding_set: BindingSet, info: KnowledgeInteraction
    ) -> BindingSet:
        nonlocal max_observed, current
        async with lock:
            current += 1
            if current > max_observed:
                max_observed = current
        await asyncio.sleep(0.05)
        async with lock:
            current -= 1
        return binding_set

    await kb.register()

    # Enqueue 5 requests but allow only 2 concurrent
    for i in range(5):
        client.enqueue_handle_request("counting-ki", [{"s": f"ex:{i}"}])
    client.enqueue_exit()

    await kb.start_handling_loop(max_concurrent_handlers=2)

    assert len(client._handle_responses) == 5
    assert max_observed <= 2, f"Concurrency exceeded limit: {max_observed}"


async def test_event_loop_stored_on_kb(client: TestClient):
    """start_handling_loop() stores the running event loop on the KB instance."""
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="test",
        ke_url="http://fake-ke",
    )
    kb.client = client

    @kb.answer_ki(name="noop-ki", graph_pattern="?s ?p ?o .")
    async def noop(binding_set: BindingSet, info: KnowledgeInteraction) -> BindingSet:
        return binding_set

    await kb.register()
    client.enqueue_exit()

    assert not hasattr(kb, "_loop")
    await kb.start_handling_loop()
    assert kb._loop is asyncio.get_running_loop()
