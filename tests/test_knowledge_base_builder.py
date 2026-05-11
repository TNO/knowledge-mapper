import pytest

from src import KnowledgeBase, KnowledgeBaseSettings
from src.ke.models import (
    AskAnswerInteractionInfo,
    BindingSet,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteractionInfo,
    PostReactInteractionInfo,
)
from src.knowledge_base_builder import KnowledgeBaseBuilder


def settings_factory(
    ki_infos: list[KnowledgeInteractionInfo] | None = None,
) -> KnowledgeBaseSettings:
    return KnowledgeBaseSettings(
        knowledge_base=KnowledgeBaseInfo(
            id="http://example.org/test#builder-kb",
            name="builder-kb",
            description="A KB for testing the builder.",
        ),
        knowledge_engine_endpoint="http://fake-ke",
        knowledge_interactions=ki_infos or [],
    )


def answer_ki_info(name: str = "answer-ki") -> AskAnswerInteractionInfo:
    return AskAnswerInteractionInfo(
        name=name, type=KiTypes.ANSWER, graph_pattern="?s ?p ?o ."
    )


def ask_ki_info(name: str = "ask-ki") -> AskAnswerInteractionInfo:
    return AskAnswerInteractionInfo(
        name=name, type=KiTypes.ASK, graph_pattern="?s ?p ?o ."
    )


def post_ki_info(name: str = "post-ki") -> PostReactInteractionInfo:
    return PostReactInteractionInfo(
        name=name,
        type=KiTypes.POST,
        argument_graph_pattern="?s ?p ?o .",
        result_graph_pattern="?s ?p ?o .",
    )


def react_ki_info(name: str = "react-ki") -> PostReactInteractionInfo:
    return PostReactInteractionInfo(
        name=name,
        type=KiTypes.REACT,
        argument_graph_pattern="?s ?p ?o .",
        result_graph_pattern="?s ?p ?o .",
    )


def dummy_handler(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    return binding_set


# --- Tracer bullet ---


def test_from_settings_returns_builder():
    settings = settings_factory()
    builder = KnowledgeBase.from_settings(settings)
    assert isinstance(builder, KnowledgeBaseBuilder)


# --- build() ---


def test_build_returns_knowledge_base_with_correct_info():
    settings = settings_factory()
    builder = KnowledgeBase.from_settings(settings)
    kb = builder.build()
    assert isinstance(kb, KnowledgeBase)
    assert kb.info.id == settings.knowledge_base.id
    assert kb.info.name == settings.knowledge_base.name


def test_build_with_only_outgoing_kis_succeeds():
    """ASK and POST KIs need no handler; build() should succeed and register them."""
    settings = settings_factory([ask_ki_info(), post_ki_info()])
    builder = KnowledgeBase.from_settings(settings)
    kb = builder.build()
    assert "ask-ki" in kb.ki_registry
    assert "post-ki" in kb.ki_registry


def test_build_raises_when_incoming_ki_has_no_handler():
    """build() must fail if an ANSWER or REACT KI from settings has no handler."""
    settings = settings_factory([answer_ki_info()])
    builder = KnowledgeBase.from_settings(settings)
    with pytest.raises(ValueError, match="answer-ki"):
        builder.build()


# --- handler() ---


def test_handler_attaches_to_answer_ki():
    settings = settings_factory([answer_ki_info()])
    builder = KnowledgeBase.from_settings(settings)
    builder.handler("answer-ki", dummy_handler)
    kb = builder.build()
    assert "answer-ki" in kb.ki_registry


def test_handler_attaches_to_react_ki():
    settings = settings_factory([react_ki_info()])
    builder = KnowledgeBase.from_settings(settings)
    builder.handler("react-ki", dummy_handler)
    kb = builder.build()
    assert "react-ki" in kb.ki_registry


def test_handler_raises_for_ki_not_in_settings():
    settings = settings_factory([answer_ki_info()])
    builder = KnowledgeBase.from_settings(settings)
    with pytest.raises(ValueError, match="nonexistent"):
        builder.handler("nonexistent", dummy_handler)


def test_handler_raises_for_ask_ki():
    """handler() is only for incoming (ANSWER/REACT) KIs."""
    settings = settings_factory([ask_ki_info()])
    builder = KnowledgeBase.from_settings(settings)
    with pytest.raises(ValueError):
        builder.handler("ask-ki", dummy_handler)


def test_handler_raises_for_post_ki():
    settings = settings_factory([post_ki_info()])
    builder = KnowledgeBase.from_settings(settings)
    with pytest.raises(ValueError):
        builder.handler("post-ki", dummy_handler)


def test_build_with_all_ki_types():
    """Full round-trip: all four KI types from settings."""
    settings = settings_factory(
        [ask_ki_info(), answer_ki_info(), post_ki_info(), react_ki_info()]
    )
    builder = KnowledgeBase.from_settings(settings)
    builder.handler("answer-ki", dummy_handler)
    builder.handler("react-ki", dummy_handler)
    kb = builder.build()
    assert "ask-ki" in kb.ki_registry
    assert "answer-ki" in kb.ki_registry
    assert "post-ki" in kb.ki_registry
    assert "react-ki" in kb.ki_registry


# --- KnowledgeBase no longer has settings-related API ---


def test_knowledge_base_has_no_build_settings():
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test",
        description="test",
        ke_url="http://fake-ke",
    )
    assert not hasattr(kb, "_build_settings")


def test_knowledge_base_has_no_ki_from_settings():
    kb = KnowledgeBase(
        id="http://example.org/test#kb",
        name="test",
        description="test",
        ke_url="http://fake-ke",
    )
    assert not hasattr(kb, "ki_from_settings")
    assert not hasattr(kb, "ki_from_settings_with_default_handler")
