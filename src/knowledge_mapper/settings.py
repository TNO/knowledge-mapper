from typing import Annotated, Any

from pydantic import Discriminator, Field, Tag
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from .ke.models import (
    AskAnswerKnowledgeInteraction,
    KiTypes,
    KnowledgeBaseInfo,
    KnowledgeInteraction,
    PostReactKnowledgeInteraction,
)


def _ki_discriminator(v: Any) -> str:
    if isinstance(v, dict):
        t = v.get("type") or v.get("knowledgeInteractionType")
    else:
        t = getattr(v, "type", None)
    if t in (
        KiTypes.ASK,
        KiTypes.ANSWER,
        KiTypes.ASK.value,
        KiTypes.ANSWER.value,
    ):
        return "ask_answer"
    if t in (
        KiTypes.POST,
        KiTypes.REACT,
        KiTypes.POST.value,
        KiTypes.REACT.value,
    ):
        return "post_react"
    raise ValueError(f"Unknown knowledge interaction type: {t!r}")


KnowledgeInteractionUnion = Annotated[
    Annotated[AskAnswerKnowledgeInteraction, Tag("ask_answer")]
    | Annotated[PostReactKnowledgeInteraction, Tag("post_react")],
    Discriminator(_ki_discriminator),
]


class KnowledgeBaseSettings(BaseSettings):
    """Base settings for a KE Knowledge Base application, based on Pydantic
    BaseSettings.

    Subclass this to add application-specific settings. All fields are
    populated from the following sources, in priority order (highest first):

    1. Keyword arguments
    2. Environment variables
    3. YAML config file (``yaml_file`` in ``model_config``, default ``config.yaml``)
    4. JSON config file (``json_file`` in ``model_config``, default ``config.json``)
    5. Field default values

    For CLI argument support, set ``cli_parse_args=True`` in your subclass
    ``model_config`` and include a :class:`~pydantic_settings.CliSettingsSource`
    in a custom ``settings_customise_sources`` override.

    Example::

        from pydantic_settings import CliSettingsSource, SettingsConfigDict
        from knowledge_mapper import KnowledgeBaseSettings

        class AppSettings(KnowledgeBaseSettings):
            model_config = SettingsConfigDict(
                yaml_file="config.yaml",
                env_prefix="MYAPP_",
                cli_parse_args=True,
            )

            # Application-specific fields
            database_url: str = "sqlite:///./myapp.db"
            debug: bool = False

            @classmethod
            def settings_customise_sources(cls, settings_cls, **kwargs):
                return (
                    CliSettingsSource(settings_cls, cli_parse_args=True),
                    *super().settings_customise_sources(settings_cls, **kwargs),
                )

        settings = AppSettings()
    """

    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        json_file="config.json",
        env_nested_delimiter="__",
        extra="ignore",
    )

    knowledge_base: KnowledgeBaseInfo
    knowledge_engine_endpoint: str
    knowledge_interactions: list[KnowledgeInteractionUnion] = Field(
        default_factory=list
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            JsonConfigSettingsSource(settings_cls),
        )

    def get_configured_interaction(self, name: str) -> KnowledgeInteraction:
        for ki in self.knowledge_interactions:
            if ki.name == name:
                return ki
        raise ValueError(f"No interaction found with name '{name}'")
