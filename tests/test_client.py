from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from knowledge_mapper.ke import Client
from knowledge_mapper.ke.models import (
    AskAnswerInteractionInfo,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
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
            ki=KnowledgeInteractionInfo(
                type="AskKnowledgeInteraction",
                name="ask-interaction",
                graph_pattern="?s ?p ?o . ",  # pyright: ignore[reportCallIssue]
                prefixes={"test": "http://example.org/test#"},
            ),
        )

    assert registered_ki.id == "http://example.org/test#kb/interaction/ask-interaction"
