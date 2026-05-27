"""Tests for the handling loop using TestClient's enqueue methods."""

import pytest

from knowledge_mapper import KnowledgeBase
from knowledge_mapper.ke.models import (
    BindingSet,
    KnowledgeInteractionInfo,
)
from knowledge_mapper.testing import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(fake_url="http://fake-ke")


@pytest.fixture
def kb(client: TestClient) -> KnowledgeBase:
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
    def echo_handler(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        captured.append(binding_set)
        return binding_set

    kb.register()
    kb._test_captured = captured  # type: ignore[attr-defined]
    return kb


def test_handle_dispatches_to_handler(kb: KnowledgeBase, client: TestClient):
    """Enqueueing a HANDLE request dispatches to the handler and posts a response."""
    input_bs: BindingSet = [{"s": "ex:A", "p": "ex:rel", "o": "ex:B"}]
    client.enqueue_handle_request("echo-ki", input_bs)

    kb.start_handling_loop(loops=1)

    assert kb._test_captured == [input_bs]  # type: ignore[attr-defined]
    assert client.last_handle_response == input_bs


def test_exit_stops_loop(kb: KnowledgeBase, client: TestClient):
    """An EXIT signal terminates the loop without requiring a loops limit."""
    client.enqueue_exit()
    kb.start_handling_loop()  # would hang without the EXIT signal


def test_handle_then_exit(kb: KnowledgeBase, client: TestClient):
    """A HANDLE followed by EXIT processes the request and then stops."""
    input_bs: BindingSet = [{"s": "ex:X"}]
    client.enqueue_handle_request("echo-ki", input_bs)
    client.enqueue_exit()

    kb.start_handling_loop()

    assert kb._test_captured == [input_bs]  # type: ignore[attr-defined]
    assert client.last_handle_response == input_bs


def test_multiple_handle_requests(kb: KnowledgeBase, client: TestClient):
    """Multiple HANDLE requests are processed in order."""
    bs1: BindingSet = [{"s": "ex:1"}]
    bs2: BindingSet = [{"s": "ex:2"}]
    client.enqueue_handle_request("echo-ki", bs1)
    client.enqueue_handle_request("echo-ki", bs2)
    client.enqueue_exit()

    kb.start_handling_loop()

    assert kb._test_captured == [bs1, bs2]  # type: ignore[attr-defined]
    assert len(client._handle_responses) == 2
    assert client._handle_responses[0][3] == bs1
    assert client._handle_responses[1][3] == bs2


def test_repoll_fallback(kb: KnowledgeBase, client: TestClient):
    """With nothing enqueued, a single loop iteration REPOLLs without error."""
    kb.start_handling_loop(loops=1)
    assert kb._test_captured == []  # type: ignore[attr-defined]


def test_enqueue_unknown_ki_raises(client: TestClient):
    """Enqueueing a handle request for an unregistered KI raises KeyError."""
    with pytest.raises(KeyError, match="No registered KI named 'nonexistent'"):
        client.enqueue_handle_request("nonexistent", [])
