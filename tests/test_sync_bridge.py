"""Tests for ask_sync() / post_sync() — sync bridges for outgoing KI calls."""

import pytest

from knowledge_mapper import KnowledgeBase
from knowledge_mapper.ke.models import BindingSet, KnowledgeInteractionInfo
from knowledge_mapper.testing import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(fake_url="http://fake-ke")


@pytest.fixture
async def kb(client: TestClient) -> KnowledgeBase:
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing sync bridges.",
        ke_url="http://fake-ke",
    )
    kb.client = client
    return kb


async def test_ask_sync_outside_handling_loop_raises(kb: KnowledgeBase):
    """ask_sync() raises RuntimeError when called without a running handling loop."""
    kb.ask_ki(name="my-ask", graph_pattern="?s ?p ?o .")
    await kb.register()
    await kb.sync_knowledge_interactions()

    with pytest.raises(RuntimeError, match="handling loop"):
        kb.ask_sync([{}], ki_name="my-ask")


async def test_ask_sync_from_sync_handler(
    kb: KnowledgeBase, client: TestClient
):
    """A sync handler can call ask_sync() to query the KE network."""
    kb.ask_ki(name="lookup", graph_pattern="?s ?p ?o .")
    await kb.register()
    await kb.sync_knowledge_interactions()

    client.mock_result_binding_set(
        ki_name="lookup",
        binding_set=[{"s": "ex:found"}],
    )

    ask_result_capture: list = []

    @kb.react_ki(
        name="my-react",
        argument_graph_pattern="?x a ?t .",
        result_graph_pattern="?x a ?t .",
    )
    def sync_handler(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        result = kb.ask_sync([{}], ki_name="lookup")
        ask_result_capture.append(result)
        return binding_set

    await kb.sync_knowledge_interactions()

    client.enqueue_handle_request("my-react", [{"x": "ex:A", "t": "ex:Thing"}])
    client.enqueue_exit()

    await kb.start_handling_loop()

    assert len(ask_result_capture) == 1
    assert ask_result_capture[0] == [{"s": "ex:found"}]


async def test_post_sync_outside_handling_loop_raises(kb: KnowledgeBase):
    """post_sync() raises RuntimeError when called without a running handling loop."""
    kb.post_ki(
        name="my-post",
        argument_graph_pattern="?s ?p ?o .",
        result_graph_pattern="?s ?p ?o .",
    )
    await kb.register()
    await kb.sync_knowledge_interactions()

    with pytest.raises(RuntimeError, match="handling loop"):
        kb.post_sync([{}], ki_name="my-post")


async def test_post_sync_from_sync_handler(
    kb: KnowledgeBase, client: TestClient
):
    """A sync handler can call post_sync() to push data to the KE network."""
    kb.post_ki(
        name="push",
        argument_graph_pattern="?x a ?t .",
        result_graph_pattern="?x ex:storedBy ?kb .",
        prefixes={"ex": "http://example.org/test#"},
    )
    await kb.register()
    await kb.sync_knowledge_interactions()

    client.mock_result_binding_set(
        ki_name="push",
        binding_set=[{"x": "ex:A", "kb": "ex:myKB"}],
    )

    post_result_capture: list = []

    @kb.react_ki(
        name="my-react",
        argument_graph_pattern="?x a ?t .",
        result_graph_pattern="?x a ?t .",
    )
    def sync_handler(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        result = kb.post_sync([{"x": "ex:A", "t": "ex:Thing"}], ki_name="push")
        post_result_capture.append(result)
        return binding_set

    await kb.sync_knowledge_interactions()

    client.enqueue_handle_request("my-react", [{"x": "ex:B", "t": "ex:Other"}])
    client.enqueue_exit()

    await kb.start_handling_loop()

    assert len(post_result_capture) == 1
    assert post_result_capture[0] == [{"x": "ex:A", "kb": "ex:myKB"}]
