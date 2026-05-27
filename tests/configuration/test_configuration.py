from pydantic_settings import SettingsConfigDict

from knowledge_mapper import KnowledgeBase, KnowledgeBaseSettings


def test_basic_configuration():
    class KbSettings(KnowledgeBaseSettings):
        model_config = SettingsConfigDict(
            yaml_file="tests/configuration/config.yaml",
        )

    settings = KbSettings()  # pyright: ignore[reportCallIssue]
    builder = KnowledgeBase.from_settings(settings)
    kb = builder.build()
    assert kb.info.id == settings.knowledge_base.id


def test_configuration_different_sources():
    class KbSettings(KnowledgeBaseSettings):
        model_config = SettingsConfigDict(
            yaml_file="tests/configuration/config.yaml",
            env_file="tests/configuration/.env.test",
        )

    settings = KbSettings()  # pyright: ignore[reportCallIssue]
    builder = KnowledgeBase.from_settings(settings)
    kb = builder.build()
    assert kb.info.id == "http://example.org/test/config#kb-from-env"


def test_configuration_interactions():
    class KbSettings(KnowledgeBaseSettings):
        model_config = SettingsConfigDict(
            yaml_file="tests/configuration/config-with-interactions.yaml",
        )

    settings = KbSettings()  # pyright: ignore[reportCallIssue]
    builder = KnowledgeBase.from_settings(settings)

    def answer(binding_set, info):
        return binding_set

    def react(binding_set, info):
        return binding_set

    builder.handler("answer-from-settings", answer)
    builder.handler("react-from-settings", react)

    kb = builder.build()

    ask_ki = kb.ki_registry["ask-from-settings"]
    assert ask_ki.info.name == "ask-from-settings"
    post_ki = kb.ki_registry["post-from-settings"]
    assert post_ki.info.name == "post-from-settings"
    answer_ki = kb.ki_registry["answer-from-settings"]
    assert answer_ki.info.name == "answer-from-settings"
    react_ki = kb.ki_registry["react-from-settings"]
    assert react_ki.info.name == "react-from-settings"
