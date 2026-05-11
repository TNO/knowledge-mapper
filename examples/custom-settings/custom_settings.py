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


# Subclass KnowledgeBaseSettings to add application-specific settings alongside the
# standard KB configuration fields. The model_config points to the YAML file for this
# example and enables CLI argument parsing.
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

    # Override settings_customise_sources to prepend CliSettingsSource so that CLI
    # arguments take the highest priority, followed by the sources defined in the base
    # class (env vars, config file, defaults).
    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):  # type: ignore
        return (
            CliSettingsSource(settings_cls, cli_parse_args=True),
            *super().settings_customise_sources(settings_cls, **kwargs),
        )


# Instantiate AppSettings to load configuration from all sources at once (CLI args,
# env vars, YAML file, and field defaults), in priority order.
settings = AppSettings()  # type: ignore


def example_answer_from_settings(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    return binding_set


def example_react_from_settings(
    binding_set: BindingSet, info: KnowledgeInteractionInfo
) -> BindingSet:
    return binding_set


# Use KnowledgeBase.from_settings to build the KB from the settings object instead of
# passing explicit constructor arguments. KIs defined in the settings YAML are
# registered automatically; use .handler() to attach a handler function to each of
# the ANSWER/REACT KIs by name. This is required, otherwise .build() will fail.
kb = (
    KnowledgeBase.from_settings(settings)
    .handler("answer-from-settings", example_answer_from_settings)
    .handler("react-from-settings", example_react_from_settings)
    .build()
)


if __name__ == "__main__":
    # After building, we can see that KI contexts are accessible, and so
    # are the settings from configuration sources.
    ask_ctx = kb.ki_registry["ask-from-settings"]
    post_ctx = kb.ki_registry["post-from-settings"]

    logger.info(f"KB id:          {kb.info.id}")
    logger.info(f"DB host:port:   {settings.db_host}:{settings.db_port}")
    logger.info(f"Debug:          {settings.debug}")
    logger.info(f"ASK KI name:     {ask_ctx.info.name}")
    logger.info(f"POST KI name:    {post_ctx.info.name}")
