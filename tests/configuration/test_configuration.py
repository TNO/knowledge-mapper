from pydantic_settings import SettingsConfigDict

from src import KnowledgeBase, KnowledgeBaseSettings


def test_basic_configuration():
    class KbSettings(KnowledgeBaseSettings):
        model_config = SettingsConfigDict(
            yaml_file="tests/configuration/config.yaml",
        )

    settings = KbSettings() # pyright: ignore[reportCallIssue]
    kb = KnowledgeBase.from_settings(settings)
    assert kb.info.id == settings.knowledge_base.id


def test_configuration_different_sources():
    class KbSettings(KnowledgeBaseSettings):
        model_config = SettingsConfigDict(
            yaml_file="tests/configuration/config.yaml",
            env_file="tests/configuration/.env.test",
        )

    settings = KbSettings() # pyright: ignore[reportCallIssue]
    kb = KnowledgeBase.from_settings(settings)
    assert kb.info.id == "http://example.org/test/config#kb-from-env"


def test_configuration_interactions():
    class KbSettings(KnowledgeBaseSettings):
        model_config = SettingsConfigDict(
            yaml_file="tests/configuration/config-with-interactions.yaml",
        )

    settings = KbSettings() # pyright: ignore[reportCallIssue]
    kb = KnowledgeBase.from_settings(settings)
    kb.ki_from_settings_with_default_handler("ask-from-settings")    
    kb.ki_from_settings_with_default_handler("post-from-settings")    

    ask_ki = kb.ki_registry["ask-from-settings"]
    assert ask_ki.info.name == "ask-from-settings"
    post_ki = kb.ki_registry["post-from-settings"]
    assert post_ki.info.name == "post-from-settings"

    @kb.ki_from_settings("answer-from-settings")
    def answer(binding_set, info):
        return binding_set


    @kb.ki_from_settings("react-from-settings")
    def react(binding_set, info):
        return binding_set

    answer_ki = kb.ki_registry["answer-from-settings"]
    assert answer_ki.info.name == "answer-from-settings"
    react_ki = kb.ki_registry["react-from-settings"]
    assert react_ki.info.name == "react-from-settings"