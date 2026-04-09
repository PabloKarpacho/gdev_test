from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_env_file(base_dir: Path | None = None) -> str | None:
    """
    ### Purpose
    Resolve the first available project-local environment file.

    ### Parameters
    - **base_dir** (Path | None): Base project directory to search in.

    ### Returns
    - **str | None**: Path to an existing env file or `None` if nothing was found.
    """

    search_root = base_dir or PROJECT_ROOT
    for candidate in (search_root / "local.env", search_root / ".env"):
        if candidate.exists():
            return str(candidate)
    return None


class Settings(BaseSettings):
    """
    ### Purpose
    Store runtime configuration loaded from environment variables.

    ### Parameters
    - **BaseSettings**: The parent class provides env-based loading.

    ### Returns
    - **Settings**: Pydantic settings model instance.
    """

    model_config = SettingsConfigDict(
        env_file=resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    bot_token: str = Field(
        ...,
        validation_alias=AliasChoices("BOT_TOKEN", "BOT_CLIENT_TOKEN"),
        description="Telegram bot token.",
    )
    openai_api_key: str = Field(
        ...,
        validation_alias=AliasChoices("OPENAI_API_KEY", "OPENAI_API_TOKEN"),
        description="OpenAI API key.",
    )
    openai_chat_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices("OPENAI_CHAT_MODEL", "OPENAI_MODEL"),
        description="OpenAI chat model used by ChatOpenAI.",
    )
    openai_transcription_model: str = Field(
        default="gpt-4o-mini-transcribe",
        validation_alias=AliasChoices(
            "OPENAI_TRANSCRIPTION_MODEL",
            "OPENAI_AUDIO_MODEL",
        ),
        description="OpenAI transcription model for voice messages.",
    )
    system_prompt: str = Field(
        default=(
            "You are a helpful Telegram assistant. "
            "Answer clearly, concisely, and use the user's message context."
        ),
        description="System prompt for the AI assistant.",
    )
    log_level: str = Field(default="INFO", description="Application log level.")

    @property
    def openai_model(self) -> str:
        """
        ### Purpose
        Provide a backward-compatible alias for the chat model field.

        ### Parameters
        - **None**: The property reads the validated settings state.

        ### Returns
        - **str**: Chat model name used by the application.
        """

        return self.openai_chat_model


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """
    ### Purpose
    Load and cache validated application settings.

    ### Parameters
    - **None**: Configuration is resolved from environment variables and env files.

    ### Returns
    - **Settings**: Cached validated settings instance.
    """

    return Settings()


class LazySettingsProxy:
    """
    ### Purpose
    Delay settings validation until values are actually requested.

    ### Parameters
    - **None**: The proxy forwards attribute access to cached settings.

    ### Returns
    - **LazySettingsProxy**: Proxy object used as a module-level settings reference.
    """

    def __getattr__(self, item: str):
        return getattr(load_settings(), item)


settings = LazySettingsProxy()
