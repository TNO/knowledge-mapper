from unittest.mock import AsyncMock, patch

import pytest

from knowledge_mapper import KnowledgeBase
from knowledge_mapper.kb.knowledge_base import KnowledgeBaseState
from knowledge_mapper.ke.errors import KnowledgeEngineNotAvailableError
from knowledge_mapper.testing import TestClient


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


async def test_connect_to_ke(kb: KnowledgeBase):
    await kb.connect()  # Should not raise an exception


async def test_connect_raises_if_ke_unavailable(kb: KnowledgeBase):
    with (
        patch.object(
            kb.client,
            "ke_is_available",
            new_callable=AsyncMock,
            return_value=False,
        ),
        pytest.raises(KnowledgeEngineNotAvailableError),
    ):
        await kb.connect()


async def test_register_unregister_cycle(kb: KnowledgeBase, client: TestClient):
    await kb.connect()
    await kb.register()
    assert kb.state == KnowledgeBaseState.REGISTERED
    assert await client.get_knowledge_base(kb.info.id) is not None
    await kb.unregister()
    assert kb.state == KnowledgeBaseState.UNREGISTERED
    assert await client.get_knowledge_base(kb.info.id) is None


async def test_unregister_without_registering(kb: KnowledgeBase):
    await kb.connect()
    await kb.unregister()  # Should not raise an exception, just log a warning


async def test_start_handling_loop_without_registering(kb: KnowledgeBase):
    with pytest.raises(RuntimeError):
        await kb.start_handling_loop(loops=1)


async def test_close_delegates_to_client(kb: KnowledgeBase, client: TestClient):
    await kb.connect()
    await kb.register()
    await kb.close()  # Should not raise; delegates to client.close()
