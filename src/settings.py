from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from src.ke.models import KnowledgeBaseInfo, KnowledgeInteractionInfo


class KnowledgeBaseSettings(BaseSettings):
    """Base settings for a KE Knowledge Base application, based on Pydantic
    BaseSettings.

    Subclass this to add application-specific settings. All fields are
    populated from the following sources, in priority order (highest first):

    1. Initialiser keyword arguments
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
    knowledge_interactions: list[KnowledgeInteractionInfo] = Field(default_factory=list)

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

    def interaction_by_name(self, name: str) -> KnowledgeInteractionInfo:
        for ki in self.knowledge_interactions:
            if ki.name == name:
                return ki
        raise ValueError(f"No interaction found with name '{name}'")
