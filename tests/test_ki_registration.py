from src.ke.models import BindingSet, KiTypes
from src.knowledge_base import KnowledgeBase
from tests.fake_client import FakeClient


# Not a fixture as a fresh KB instance is needed for each test.
def kb_setup() -> KnowledgeBase:
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )
    kb.client = FakeClient(fake_url="http://fake-ke")
    return kb


def shared_prefixes():
    return {
        "test": "http://example.org/test#",
    }


def test_register_answer_ki():
    kb = kb_setup()

    @kb.answer_ki(
        name="answer-test",
        graph_pattern="""
            ?question a test:Question .
            ?question test:hasText ?text .
        """,
        prefixes=shared_prefixes(),
    )
    def answer_test():
        pass

    kb.register()

    assert len(kb.ki_registry) == 1
    ki_info = next(iter(kb.ki_registry.values())).info
    assert ki_info.name == "answer-test"
    assert ki_info.type == KiTypes.ANSWER


def test_register_react_ki():
    kb = kb_setup()

    @kb.react_ki(
        name="react-test",
        argument_graph_pattern="""
            ?event a test:Event .
            ?event test:hasDescription ?desc .
        """,
        result_graph_pattern="""
            ?reaction a test:Reaction .
            ?reaction test:reactsTo ?event .
        """,
        prefixes=shared_prefixes(),
    )
    def react_test():
        pass

    kb.register()

    assert len(kb.ki_registry) == 1
    ki_info = next(iter(kb.ki_registry.values())).info
    assert ki_info.name == "react-test"
    assert ki_info.type == KiTypes.REACT


def test_handler_registration_no_binding_set_param():
    kb = kb_setup()

    try:

        @kb.answer_ki(
            name="bad-handler",
            graph_pattern="""""",
        )
        def bad_handler():
            pass

    except ValueError as e:
        assert str(e) == "Handler must have a 'binding_set' parameter."
    else:
        raise AssertionError(
            "Expected ValueError for handler with incorrect parameters."
        )


def test_call_handler():
    kb = kb_setup()

    @kb.answer_ki(
        name="echo-handler",
        graph_pattern="""
            ?input a test:Input .
            ?input test:hasValue ?value .
        """,
        prefixes=shared_prefixes(),
    )
    def echo_handler(binding_set: BindingSet) -> BindingSet:
        return binding_set

    kb.register()

    ki_info = next(iter(kb.ki_registry.values())).info
    input_binding_set = [{"input": "test:Input1", "value": "Hello"}]
    result = kb.call(binding_set=input_binding_set, ki=ki_info)
    assert result == input_binding_set