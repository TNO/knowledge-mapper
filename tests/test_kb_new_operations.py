"""Tests for KnowledgeBase wrappers around the three new client operations:

- ``unregister_ki(ki_name)``
- ``renew_lease()``
- ``load_domain_knowledge(knowledge)``
"""

import pytest

from knowledge_mapper import KnowledgeBase
from knowledge_mapper.ke.errors import SmartConnectorNotFoundError
from knowledge_mapper.ke.models import (
    KnowledgeInteractionInfo,
    SmartConnectorLease,
)
from knowledge_mapper.testing import TestClient


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )
    kb.client = TestClient(fake_url="http://fake-ke")
    return kb


async def test_unregister_ki_removes_from_registries_and_calls_client():
    kb = _kb()
    await kb.register()
    await kb.register_ki(
        ki_ctx=_ki_ctx("ask-it"),
    )
    assert "ask-it" in kb.ki_registry
    ki_id = kb.ki_registry["ask-it"].info.id
    assert ki_id is not None and ki_id in kb._ki_registry_by_id

    await kb.unregister_ki("ask-it")

    assert "ask-it" not in kb.ki_registry
    assert ki_id not in kb._ki_registry_by_id
    assert await kb.client.get_all_knowledge_interactions(kb.info.id) == []


async def test_unregister_ki_raises_when_kb_not_registered():
    kb = _kb()
    with pytest.raises(ValueError, match="not registered"):
        await kb.unregister_ki("ask-it")


async def test_unregister_ki_raises_for_unknown_ki():
    kb = _kb()
    await kb.register()
    with pytest.raises(ValueError, match="no KI with that name"):
        await kb.unregister_ki("does-not-exist")


async def test_renew_lease_returns_lease_and_invokes_client():
    kb = _kb()
    await kb.register()

    lease = await kb.renew_lease()

    assert isinstance(lease, SmartConnectorLease)
    assert lease.knowledge_base_id == kb.info.id
    # The TestClient tracks how often renew_lease was called per KB id.
    assert kb.client.lease_renewals[kb.info.id] == 1  # pyright: ignore[reportAttributeAccessIssue]


async def test_renew_lease_unknown_kb_raises():
    kb = _kb()
    await kb.register()
    # Simulate the KB disappearing from the runtime.
    await kb.client.unregister_kb(kb.info.id)
    with pytest.raises(SmartConnectorNotFoundError):
        await kb.renew_lease()


async def test_renew_lease_when_kb_not_registered_raises():
    kb = _kb()
    with pytest.raises(ValueError, match="not registered"):
        await kb.renew_lease()


async def test_load_domain_knowledge_stores_payload():
    kb = _kb()
    await kb.register()

    knowledge = "-> ( saref:Sensor rdfs:subClassOf saref:Device) ."
    await kb.load_domain_knowledge(knowledge)

    assert kb.client.loaded_domain_knowledge[kb.info.id] == knowledge  # pyright: ignore[reportAttributeAccessIssue]


async def test_load_domain_knowledge_when_kb_not_registered_raises():
    kb = _kb()
    with pytest.raises(ValueError, match="not registered"):
        await kb.load_domain_knowledge("-> ( a b c ) .")


def _ki_ctx(name: str):
    """Build a registered ASK-style KI context for use in unregister tests."""
    from knowledge_mapper.ke.models import AskAnswerInteractionInfo, KiTypes
    from knowledge_mapper.knowledge_interaction import (
        KnowledgeInteractionContext,
        KnowledgeInteractionStatus,
    )

    return KnowledgeInteractionContext[KnowledgeInteractionInfo, ...](
        info=AskAnswerInteractionInfo(
            type=KiTypes.ASK,
            name=name,
            graph_pattern="?s ?p ?o . ",
        ),
        handler=None,
        status=KnowledgeInteractionStatus.UNREGISTERED,
    )
