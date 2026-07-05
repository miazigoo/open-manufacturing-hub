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
    auto_install_packages: str = Field(default="", validation_alias=AliasChoices("OMH_AUTO_INSTALL_PACKAGES", "AUTO_INSTALL_PACKAGES"))
    allow_demo_seed_in_production: bool = Field(default=False, validation_alias=AliasChoices("ALLOW_DEMO_SEED_IN_PRODUCTION", "OMH_ALLOW_DEMO_SEED_IN_PRODUCTION"))
    notification_webhook_timeout_seconds: float = 3.0
    notification_webhook_retries: int = 2
    sync_processing_timeout_seconds: float = 30.0
    queue_lock_seconds: int = 300
    queue_worker_batch_size: int = 10
    audit_retention_days: int = Field(default=180, validation_alias=AliasChoices("AUDIT_RETENTION_DAYS", "OMH_AUDIT_RETENTION_DAYS"))
    secret_key: str | None = Field(default=None, validation_alias=AliasChoices("OMH_SECRET_KEY", "SECRET_KEY"))
    config_require_test_before_publish: bool | None = Field(default=None, validation_alias=AliasChoices("REQUIRE_TEST_BEFORE_PUBLISH", "OMH_REQUIRE_TEST_BEFORE_PUBLISH"))
    config_require_comment_on_publish: bool | None = Field(default=None, validation_alias=AliasChoices("REQUIRE_COMMENT_ON_PUBLISH", "OMH_REQUIRE_COMMENT_ON_PUBLISH"))
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias=AliasChoices("CORS_ORIGINS", "OMH_CORS_ALLOW_ORIGINS"),
    )
    cors_allow_origin_regex: str | None = Field(
        default=r"^https?://(localhost|127\.0\.0\.1):\d+$",
        validation_alias=AliasChoices("CORS_ALLOW_ORIGIN_REGEX", "OMH_CORS_ALLOW_ORIGIN_REGEX"),
    )

    model_config = SettingsConfigDict(env_file=".env", env_prefix="OMH_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
