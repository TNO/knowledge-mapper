from src.ke.models import KiTypes
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
    ki_info = next(iter(kb.ki_registry.values()))
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
    ki_info = next(iter(kb.ki_registry.values()))
    assert ki_info.name == "react-test"
    assert ki_info.type == KiTypes.REACT
