"""Example: combining application config with KnowledgeBaseSettings.

Configuration is loaded automatically from (highest priority first):
  1. CLI arguments       --kb_id, --db_host, ...
  2. Environment vars    KB_ID, DB_HOST, ...
  3. config.yaml / config.json
  4. Field default values

Run:
  python custom_settings.py                          # use config.yaml / env vars
  python custom_settings.py --kb_id http://my/kb     # override via CLI
  KB_ID=http://my/kb python custom_settings.py       # override via env var
"""

from pydantic_settings import CliSettingsSource, SettingsConfigDict

from src import KnowledgeBase, KnowledgeBaseSettings
from src.ke.models import BindingSet, KnowledgeInteractionInfo


class AppSettings(KnowledgeBaseSettings):
    model_config = SettingsConfigDict(
        yaml_file="settings.yaml",
        env_prefix="",  # e.g. KB_ID, DB_HOST (no extra prefix)
        cli_parse_args=True,
        extra="ignore",
    )

    # Application-specific fields
    db_host: str = "localhost"
    db_port: int = 5432
    debug: bool = False

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):  # type: ignore
        return (
            CliSettingsSource(settings_cls, cli_parse_args=True),
            *super().settings_customise_sources(settings_cls, **kwargs),
        )


settings = AppSettings()  # type: ignore
kb = KnowledgeBase.from_settings(settings)


@kb.ki_from_info(info=settings.interaction_by_name("answer-from-settings"))
def example_answer_from_settings(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    return binding_set


@kb.ki_from_info(info=settings.interaction_by_name("react-from-settings"))
def example_react_from_settings(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    return binding_set


if __name__ == "__main__":
    ask_ctx = kb.ki_registry["ask-from-settings"]
    post_ctx = kb.ki_registry["post-from-settings"]

    print(f"KB id:          {kb.info.id}")
    print(f"DB host:port:   {settings.db_host}:{settings.db_port}")
    print(f"Debug:          {settings.debug}")
