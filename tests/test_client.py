from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from knowledge_mapper.ke import Client
from knowledge_mapper.ke.errors import (
    SmartConnectorNotFoundError,
    UnexpectedHttpResponseError,
)
from knowledge_mapper.ke.models import (
    AskAnswerInteractionInfo,
    AskAnswerKnowledgeInteraction,
    KnowledgeBaseInfo,
    PostReactInteractionInfo,
    SmartConnectorLease,
)


@pytest.fixture
def client():
    return Client(ke_url="http://fake-ke")


async def test_register_knowledge_base(client: Client):
    mock_get_response = MagicMock()
    mock_get_response.status_code = 404

    mock_post_response = MagicMock()
    mock_post_response.is_success = True

    with (
        patch.object(
            client._http,
            "get",
            new_callable=AsyncMock,
            return_value=mock_get_response,
        ) as mock_get,
        patch.object(
            client._http,
            "post",
            new_callable=AsyncMock,
            return_value=mock_post_response,
        ) as mock_post,
    ):
        await client.register_kb(
            info=KnowledgeBaseInfo(
                id="http://example.org/test#kb",
                name="test-kb",
                description="A KB for testing.",
            )
        )

    mock_get.assert_called_once_with(
        "http://fake-ke/sc",
        headers={"Knowledge-Base-Id": "http://example.org/test#kb"},
    )
    mock_post.assert_called_once_with(
        "http://fake-ke/sc",
        json={
            "knowledgeBaseId": "http://example.org/test#kb",
            "knowledgeBaseName": "test-kb",
            "knowledgeBaseDescription": "A KB for testing.",
        },
    )


async def test_get_knowledge_base(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = [
        {
            "knowledgeBaseId": "http://example.org/test#kb",
            "knowledgeBaseName": "test-kb",
            "knowledgeBaseDescription": "A KB for testing.",
        }
    ]

    with patch.object(
        client._http,
        "get",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_get:
        kb_info = await client.get_knowledge_base("http://example.org/test#kb")

    mock_get.assert_called_once_with(
        "http://fake-ke/sc", headers={"Knowledge-Base-Id": "http://example.org/test#kb"}
    )
    assert kb_info == KnowledgeBaseInfo(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
    )


async def test_get_knowledge_base_not_found(client: Client):
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.object(
        client._http,
        "get",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_get:
        kb_info = await client.get_knowledge_base("http://example.org/nonexistent-kb")

    mock_get.assert_called_once_with(
        "http://fake-ke/sc",
        headers={"Knowledge-Base-Id": "http://example.org/nonexistent-kb"},
    )
    assert kb_info is None


async def test_get_knowledge_interactions(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = [
        {
            "knowledgeInteractionType": "AskKnowledgeInteraction",
            "knowledgeInteractionId": "http://example.org/test#kb/interaction/ask-interaction",
            "knowledgeInteractionName": "ask-interaction",
            "graphPattern": "?s ?p ?o . ",
            "prefixes": {"test": "http://example.org/test#"},
        },
        {
            "knowledgeInteractionType": "PostKnowledgeInteraction",
            "knowledgeInteractionId": "http://example.org/test#kb/interaction/post-interaction",
            "knowledgeInteractionName": "post-interaction",
            "argumentGraphPattern": "?s ?p ?o . ",
            "resultGraphPattern": "?s ?p ?o . ",
            "prefixes": {"test": "http://example.org/test#"},
        },
    ]

    with patch.object(
        client._http,
        "get",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_get:
        interactions = await client.get_all_knowledge_interactions(
            "http://example.org/test#kb"
        )

    mock_get.assert_called_once_with(
        "http://fake-ke/sc/ki",
        headers={"Knowledge-Base-Id": "http://example.org/test#kb"},
    )
    assert len(interactions) == 2
    assert interactions[0].type == "AskKnowledgeInteraction"
    assert interactions[0].name == "ask-interaction"
    assert isinstance(interactions[0], AskAnswerInteractionInfo)
    assert interactions[0].graph_pattern == "?s ?p ?o . "
    assert interactions[1].type == "PostKnowledgeInteraction"
    assert interactions[1].name == "post-interaction"
    assert isinstance(interactions[1], PostReactInteractionInfo)
    assert interactions[1].argument_graph_pattern == "?s ?p ?o . "
    assert interactions[1].result_graph_pattern == "?s ?p ?o . "


async def test_register_knowledge_interaction(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "knowledgeInteractionId": "http://example.org/test#kb/interaction/ask-interaction"
    }

    with patch.object(
        client._http,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        registered_ki = await client.register_ki(
            kb_id="http://example.org/test#kb",
            ki=AskAnswerKnowledgeInteraction(
                type="AskKnowledgeInteraction",
                name="ask-interaction",
                graph_pattern="?s ?p ?o . ",
                prefixes={"test": "http://example.org/test#"},
            ),
        )

    assert registered_ki.id == "http://example.org/test#kb/interaction/ask-interaction"


async def test_register_knowledge_base_with_optional_fields(client: Client):
    """leaseRenewalTime / reasonerLevel are sent only when set (no None in payload)."""
    mock_get_response = MagicMock()
    mock_get_response.status_code = 404

    mock_post_response = MagicMock()
    mock_post_response.is_success = True

    with (
        patch.object(
            client._http,
            "get",
            new_callable=AsyncMock,
            return_value=mock_get_response,
        ),
        patch.object(
            client._http,
            "post",
            new_callable=AsyncMock,
            return_value=mock_post_response,
        ) as mock_post,
    ):
        await client.register_kb(
            info=KnowledgeBaseInfo(
                id="http://example.org/test#kb",
                name="test-kb",
                description="A KB for testing.",
                lease_renewal_time=60,
                reasoner_level=4,
            )
        )

    mock_post.assert_called_once_with(
        "http://fake-ke/sc",
        json={
            "knowledgeBaseId": "http://example.org/test#kb",
            "knowledgeBaseName": "test-kb",
            "knowledgeBaseDescription": "A KB for testing.",
            "leaseRenewalTime": 60,
            "reasonerLevel": 4,
        },
    )


async def test_register_knowledge_base_omits_unset_optional_fields(client: Client):
    """Optional fields must NOT appear in the request payload when unset."""
    mock_get_response = MagicMock()
    mock_get_response.status_code = 404

    mock_post_response = MagicMock()
    mock_post_response.is_success = True

    with (
        patch.object(
            client._http,
            "get",
            new_callable=AsyncMock,
            return_value=mock_get_response,
        ),
        patch.object(
            client._http,
            "post",
            new_callable=AsyncMock,
            return_value=mock_post_response,
        ) as mock_post,
    ):
        await client.register_kb(
            info=KnowledgeBaseInfo(
                id="http://example.org/test#kb",
                name="test-kb",
                description="A KB for testing.",
            )
        )

    payload = mock_post.call_args.kwargs["json"]
    assert "leaseRenewalTime" not in payload
    assert "reasonerLevel" not in payload


async def test_unregister_knowledge_interaction(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200

    with patch.object(
        client._http,
        "delete",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_delete:
        await client.unregister_ki(
            kb_id="http://example.org/test#kb",
            ki_id="http://example.org/test#kb/interaction/ask-interaction",
        )

    mock_delete.assert_called_once_with(
        "http://fake-ke/sc/ki",
        headers={
            "Knowledge-Base-Id": "http://example.org/test#kb",
            "Knowledge-Interaction-Id": (
                "http://example.org/test#kb/interaction/ask-interaction"
            ),
        },
    )


async def test_unregister_knowledge_interaction_not_found(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 404

    with (
        patch.object(
            client._http,
            "delete",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
        pytest.raises(SmartConnectorNotFoundError),
    ):
        await client.unregister_ki(
            kb_id="http://example.org/missing#kb",
            ki_id="http://example.org/missing#kb/interaction/x",
        )


async def test_unregister_knowledge_interaction_unexpected_response(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 500

    with (
        patch.object(
            client._http,
            "delete",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
        pytest.raises(UnexpectedHttpResponseError),
    ):
        await client.unregister_ki(
            kb_id="http://example.org/test#kb",
            ki_id="http://example.org/test#kb/interaction/x",
        )


async def test_renew_lease(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "knowledgeBaseId": "http://example.org/test#kb",
        "expires": "2026-06-25T12:00:00+00:00",
    }

    with patch.object(
        client._http,
        "put",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_put:
        lease = await client.renew_lease("http://example.org/test#kb")

    mock_put.assert_called_once_with(
        "http://fake-ke/sc/lease/renew",
        headers={"Knowledge-Base-Id": "http://example.org/test#kb"},
    )
    assert isinstance(lease, SmartConnectorLease)
    assert lease.knowledge_base_id == "http://example.org/test#kb"


async def test_renew_lease_not_found(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 404

    with (
        patch.object(
            client._http,
            "put",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
        pytest.raises(SmartConnectorNotFoundError),
    ):
        await client.renew_lease("http://example.org/missing#kb")


async def test_load_domain_knowledge(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200

    knowledge = "-> ( saref:Sensor rdfs:subClassOf saref:Device ) ."

    with patch.object(
        client._http,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_post:
        await client.load_domain_knowledge(
            kb_id="http://example.org/test#kb",
            knowledge=knowledge,
        )

    mock_post.assert_called_once_with(
        "http://fake-ke/sc/knowledge",
        content=knowledge.encode("utf-8"),
        headers={
            "Knowledge-Base-Id": "http://example.org/test#kb",
            "Content-Type": "text/plain; charset=UTF-8",
        },
    )


async def test_load_domain_knowledge_not_found(client: Client):
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 404

    with (
        patch.object(
            client._http,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
        pytest.raises(SmartConnectorNotFoundError),
    ):
        await client.load_domain_knowledge(
            kb_id="http://example.org/missing#kb",
            knowledge="-> ( a b c ) .",
        )
