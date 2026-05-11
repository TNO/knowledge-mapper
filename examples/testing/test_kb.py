import pytest
from rdflib import URIRef

from src.ke.testing import TestClient

# Import the Knowledge Base that you would like to test, along with any relevant binding
# models.
from .kb import TestBinding, ask_for_values_of_subject, kb, repeat_value_post

# In your tests you likely want to use the TestClient to mock results from the KE.
# A Knowledge Base instance is initialized with a real Client that makes HTTP requests
# to the KE, so its important to replace it with a TestClient
test_client = TestClient(fake_url="http://fake-ke")
kb.client = test_client
# Here the KB and its interactions are registered with the TestClient, which always
# succeeds. This registration is necessary for the KB to be able to execute
# interactions in the tests.
kb.register()

@pytest.fixture()
def client():
    return test_client

# In a test you can do any ASK interaction that is registered.
# The TestClient will return an empty result binding set by default, disregarding the
# input.
def test_ask_ki_no_resuls():
    result_binding_set = kb.ask([], "ask-ki-no-binding-model")
    assert result_binding_set == []


# You likely want to mock result binding sets, which can be done using the TestClient as
# in this test. The mocked result is returned when the ASK interaction is executed,
# disregarding the input.
def test_ask_ki_with_result(client: TestClient):
    client.mock_result_binding_set(
        "ask-ki-no-binding-model",
        [
            {
                "s": "<http://example.org/knowledge-mapper/testing#Subject>",
                "value": "test value",
            }
        ],
    )
    result_binding_set = kb.ask([], "ask-ki-no-binding-model")
    assert result_binding_set == [
        {
            "s": "<http://example.org/knowledge-mapper/testing#Subject>",
            "value": "test value",
        }
    ]


# This is a little more useful when you have a binding model, testing the correctness of
# the binding model according to the graph pattern. One test per interaction like this
# per interaction is probably a good idea, to isolate issues with the binding model from
# other issues.
def test_ask_ki_with_binding_model(client: TestClient):
    client.mock_result_binding_set(
        "ask-ki-with-binding-model",
        [
            {
                "s": "<http://example.org/knowledge-mapper/testing#Subject>",
                "value": "test value",
            }
        ],
    )

    result_binding_set = kb.ask(
        [
            TestBinding(
                s=URIRef("http://example.org/knowledge-mapper/testing#Subject"),
                value=None,
            )
        ],
        "ask-ki-with-binding-model",
    )
    assert result_binding_set == [
        TestBinding(
            s=URIRef("http://example.org/knowledge-mapper/testing#Subject"),
            value="test value",
        )
    ]


# However, most likely you will want to test the logic around interactions, where you
# might want to mock different results for different inputs.
def test_function_containing_ask(client: TestClient):
    client.mock_result_binding_set(
        ki_name="ask-ki-with-binding-model",
        binding_set=[
            TestBinding(
                s=URIRef("http://example.org/knowledge-mapper/testing#Subject"),
                value="test value",
            ).model_dump(),
        ],
    )

    result = ask_for_values_of_subject("Subject")
    assert result == ["test value"]


# Similar approaches can be taken for POST interactions.
def test_function_containing_post(client: TestClient):
    client.mock_result_binding_set(
        ki_name="post-ki",
        binding_set=[
            {
                "s": "<http://example.org/knowledge-mapper/testing#Subject>",
                "other": "<http://example.org/knowledge-mapper/testing#Other>",
            }
        ],
    )

    result = repeat_value_post("test value", 1)
    assert result == [URIRef("http://example.org/knowledge-mapper/testing#Other")]