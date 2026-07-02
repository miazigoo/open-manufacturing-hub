from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://omh:omh@localhost:5432/omh",
        validation_alias=AliasChoices("OMH_DATABASE_URL", "DATABASE_URL"),
    )
    app_name: str = "Open Manufacturing Hub"
    app_env: str = Field(default="development", validation_alias=AliasChoices("APP_ENV", "OMH_APP_ENV"))
    notification_webhook_timeout_seconds: float = 3.0
    notification_webhook_retries: int = 2
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias=AliasChoices("CORS_ORIGINS", "OMH_CORS_ALLOW_ORIGINS"),
    )

    model_config = SettingsConfigDict(env_file=".env", env_prefix="OMH_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
