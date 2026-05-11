import pytest

from src import KnowledgeBase
from src.ke.models import (
    AskAnswerInteractionInfo,
    BindingSet,
    KiTypes,
    KnowledgeInteractionInfo,
)
from src.ke.testing import TestClient
from src.knowledge_interaction import (
    KnowledgeInteractionContext,
    KnowledgeInteractionStatus,
)


# Not a fixture as a fresh KB instance is needed for each test.
def kb_setup() -> KnowledgeBase:
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test-kb",
        description="A KB for testing.",
        ke_url="http://fake-ke",
    )
    kb.client = TestClient(fake_url="http://fake-ke")
    return kb


def shared_prefixes():
    return {
        "test": "http://example.org/test#",
    }


def ki_ctx_setup() -> KnowledgeInteractionContext:
    def handler(binding_set: BindingSet, info: KnowledgeInteractionInfo) -> BindingSet:
        return binding_set

    return KnowledgeInteractionContext(
        info=AskAnswerInteractionInfo(
            name="test-ki",
            type=KiTypes.ANSWER,
            graph_pattern="""?s ?p ?o . """,
            prefixes=shared_prefixes(),
        ),
        handler=handler,
        status=KnowledgeInteractionStatus.UNREGISTERED,
    )


def test_register_ki():
    kb = kb_setup()
    kb.register()
    kb.register_ki(ki_ctx=ki_ctx_setup())
    assert len(kb.ki_registry) == 1
    ki_ctx = next(iter(kb.ki_registry.values()))
    assert ki_ctx.info.name == "test-ki"


def test_register_ki_before_kb_registration():
    kb = kb_setup()
    with pytest.raises(ValueError):
        kb.register_ki(ki_ctx=ki_ctx_setup())


def test_register_ki_old_name():
    kb = kb_setup()
    kb.register()
    ki_ctx = ki_ctx_setup()
    kb.register_ki(ki_ctx=ki_ctx)
    with pytest.raises(ValueError):
        kb.register_ki(ki_ctx=ki_ctx)


def test_register_ki_already_registered():
    kb = kb_setup()
    kb.register()
    ki_ctx = ki_ctx_setup()
    ki_ctx.status = KnowledgeInteractionStatus.REGISTERED
    with pytest.raises(ValueError):
        kb.register_ki(ki_ctx=ki_ctx)


def test_sync_ki():
    kb = kb_setup()
    kb.register()
    ki_ctx = ki_ctx_setup()
    kb.register_ki(ki_ctx=ki_ctx, defer_ke_registration=True)
    assert len(kb.ki_registry) == 1
    assert (
        next(iter(kb.ki_registry.values())).status
        == KnowledgeInteractionStatus.UNREGISTERED
    )

    kb.sync_knowledge_interactions()
    assert (
        next(iter(kb.ki_registry.values())).status
        == KnowledgeInteractionStatus.REGISTERED
    )


def test_sync_ki_before_kb_registration():
    kb = kb_setup()
    with pytest.raises(ValueError):
        kb.sync_knowledge_interactions()


def test_unregister_ki_after_kb_unregistration():
    kb = kb_setup()
    kb.register()
    ki_ctx = ki_ctx_setup()
    kb.register_ki(ki_ctx=ki_ctx)
    kb.unregister()
    assert (
        next(iter(kb.ki_registry.values())).status
        == KnowledgeInteractionStatus.UNREGISTERED
    )


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
    def answer_test(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        return binding_set

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
    def react_test(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        return binding_set

    kb.register()

    assert len(kb.ki_registry) == 1
    ki_info = next(iter(kb.ki_registry.values())).info
    assert ki_info.name == "react-test"
    assert ki_info.type == KiTypes.REACT


def test_register_ki_with_same_name():
    kb = kb_setup()

    @kb.answer_ki(
        name="duplicate-name",
        graph_pattern="""
            ?s ?p ?o .
        """,
    )
    def first_handler(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        return binding_set

    with pytest.raises(ValueError):

        @kb.react_ki(
            name="duplicate-name",
            argument_graph_pattern="""?s ?p ?o . """,
            result_graph_pattern="""?s ?p ?o . """,
        )
        def second_handler(
            binding_set: BindingSet, info: KnowledgeInteractionInfo
        ) -> BindingSet:
            return binding_set


def test_handler_registration_no_binding_set_param():
    kb = kb_setup()

    try:

        @kb.answer_ki(
            name="bad-handler",
            graph_pattern="""""",
        )  # pyright: ignore[reportArgumentType]
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
    def echo_handler(
        binding_set: BindingSet, info: KnowledgeInteractionInfo
    ) -> BindingSet:
        return binding_set

    kb.register()

    ki_info = next(iter(kb.ki_registry.values())).info
    input_binding_set = [{"input": "test:Input1", "value": "Hello"}]
    result = kb.call(binding_set=input_binding_set, ki_name=ki_info.name)
    assert result == input_binding_set
