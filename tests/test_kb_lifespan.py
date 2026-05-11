from unittest.mock import patch

import pytest

from src import KnowledgeBase
from src.ke.errors import KnowledgeEngineNotAvailableError
from src.ke.testing import TestClient
from src.knowledge_base import KnowledgeBaseState


@pytest.fixture
def client() -> TestClient:
    return TestClient(fake_url="http://fake-ke")


@pytest.fixture
def kb(client: TestClient) -> KnowledgeBase:
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )
    kb.client = client
    return kb


def test_connect_to_ke(kb: KnowledgeBase):
    kb.connect()  # Should not raise an exception


def test_connect_raises_if_ke_unavailable(kb: KnowledgeBase):
    with (
        patch.object(kb.client, "ke_is_available", return_value=False),
        pytest.raises(KnowledgeEngineNotAvailableError),
    ):
        kb.connect()


def test_register_unregister_cycle(kb: KnowledgeBase, client: TestClient):
    kb.connect()
    kb.register()
    assert kb.state == KnowledgeBaseState.REGISTERED
    assert client.get_knowledge_base(kb.info.id) is not None
    kb.unregister()
    assert kb.state == KnowledgeBaseState.UNREGISTERED
    assert client.get_knowledge_base(kb.info.id) is None


def test_unregister_without_registering(kb: KnowledgeBase):
    kb.connect()
    kb.unregister()  # Should not raise an exception, just log a warning


def test_start_handling_loop_without_registering(kb: KnowledgeBase):
    with pytest.raises(RuntimeError):
        kb.start_handling_loop(loops=1)
