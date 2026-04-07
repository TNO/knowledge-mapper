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
