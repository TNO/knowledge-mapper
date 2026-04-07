"""Example: combining application config with KnowledgeBaseSettings.

A good pattern is to subclass KnowledgeBaseSettings to add application-specific
settings, while still supporting the standard config sources (YAML/JSON file, env vars,
CLI args) for the KB configuration. Other setups are possible as well.
This example shows this method and how to build a KB, register KI's from settings for
each type of interaction.

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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic_settings import CliSettingsSource, SettingsConfigDict
from shared import get_example_logger

from src import KnowledgeBase, KnowledgeBaseSettings
from src.ke.models import BindingSet, KnowledgeInteractionInfo

EXAMPLE_NAME = "custom-settings"
logger = get_example_logger(EXAMPLE_NAME)


class AppSettings(KnowledgeBaseSettings):
    model_config = SettingsConfigDict(
        yaml_file="custom-settings/settings.yaml",
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
kb.ki_from_settings_with_default_handler("ask-from-settings")
kb.ki_from_settings_with_default_handler("post-from-settings")


@kb.ki_from_settings("answer-from-settings")
def example_answer_from_settings(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    return binding_set


@kb.ki_from_settings("react-from-settings")
def example_react_from_settings(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    return binding_set


if __name__ == "__main__":
    ask_ctx = kb.ki_registry["ask-from-settings"]
    post_ctx = kb.ki_registry["post-from-settings"]

    logger.info(f"KB id:          {kb.info.id}")
    logger.info(f"DB host:port:   {settings.db_host}:{settings.db_port}")
    logger.info(f"Debug:          {settings.debug}")
    logger.info(f"ASK KI name:     {ask_ctx.info.name}")
    logger.info(f"POST KI name:    {post_ctx.info.name}")
