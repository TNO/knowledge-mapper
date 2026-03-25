from unittest.mock import patch

import pytest

from src.ke.errors import KnowledgeEngineNotAvailableError
from src.knowledge_base import KnowledgeBase
from tests.fake_client import FakeClient


@pytest.fixture
def client() -> FakeClient:
    return FakeClient(fake_url="http://fake-ke")

@pytest.fixture
def kb(client: FakeClient) -> KnowledgeBase:
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


def test_register_unregister_cycle(kb: KnowledgeBase, client: FakeClient):
    kb.connect()
    kb.register()
    assert kb.registered
    assert client.get_knowledge_base(kb.info.id) is not None
    kb.unregister()
    assert not kb.registered
    assert client.get_knowledge_base(kb.info.id) is None
