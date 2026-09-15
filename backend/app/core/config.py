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
    app_version: str = Field(default="0.1.0", validation_alias=AliasChoices("OMH_APP_VERSION", "APP_VERSION"))
    public_base_url: str | None = Field(default=None, validation_alias=AliasChoices("PUBLIC_BASE_URL", "OMH_PUBLIC_BASE_URL"))
    public_api_base_url: str | None = Field(default=None, validation_alias=AliasChoices("PUBLIC_API_BASE_URL", "OMH_PUBLIC_API_BASE_URL"))
    production_profile: bool = Field(default=False, validation_alias=AliasChoices("OMH_PRODUCTION_PROFILE", "PRODUCTION_PROFILE"))
    auto_install_packages: str = Field(default="", validation_alias=AliasChoices("OMH_AUTO_INSTALL_PACKAGES", "AUTO_INSTALL_PACKAGES"))
    allow_demo_seed_in_production: bool = Field(default=False, validation_alias=AliasChoices("ALLOW_DEMO_SEED_IN_PRODUCTION", "OMH_ALLOW_DEMO_SEED_IN_PRODUCTION"))
    notification_webhook_timeout_seconds: float = 3.0
    notification_webhook_retries: int = 2
    sync_processing_timeout_seconds: float = 30.0
    queue_lock_seconds: int = 300
    queue_worker_batch_size: int = 10
    queue_worker_loop_interval_seconds: float = Field(default=5.0, validation_alias=AliasChoices("QUEUE_WORKER_LOOP_INTERVAL_SECONDS", "OMH_QUEUE_WORKER_LOOP_INTERVAL_SECONDS"))
    audit_retention_days: int = Field(default=180, validation_alias=AliasChoices("AUDIT_RETENTION_DAYS", "OMH_AUDIT_RETENTION_DAYS"))
    xml_max_bytes: int = Field(default=10485760, validation_alias=AliasChoices("XML_MAX_BYTES", "OMH_XML_MAX_BYTES"))
    xml_full_artifact_max_bytes: int = Field(default=1048576, validation_alias=AliasChoices("XML_FULL_ARTIFACT_MAX_BYTES", "OMH_XML_FULL_ARTIFACT_MAX_BYTES"))
    marking_code_pool_export_dir: str = Field(default="/tmp/omh-marking-code-pools", validation_alias=AliasChoices("MARKING_CODE_POOL_EXPORT_DIR", "OMH_MARKING_CODE_POOL_EXPORT_DIR"))
    dnp_chz_code_pool_import_url: str = Field(default="", validation_alias=AliasChoices("DNP_CHZ_CODE_POOL_IMPORT_URL", "OMH_DNP_CHZ_CODE_POOL_IMPORT_URL"))
    dnp_shared_secret: str = Field(default="", validation_alias=AliasChoices("OMH_DNP_SHARED_SECRET", "DNP_SHARED_SECRET"))
    # Large CHZ pools (3k+ codes) regularly need several minutes on DnP.
    # 180s caused false "forward failed" while DnP had already accepted the pool.
    dnp_request_timeout_seconds: float = Field(default=600.0, validation_alias=AliasChoices("DNP_REQUEST_TIMEOUT_SECONDS", "OMH_DNP_REQUEST_TIMEOUT_SECONDS"))
    chz_laser_file_enabled: bool = Field(default=True, validation_alias=AliasChoices("CHZ_LASER_FILE_ENABLED", "OMH_CHZ_LASER_FILE_ENABLED"))
    chz_laser_smb_unc: str = Field(default="", validation_alias=AliasChoices("CHZ_LASER_SMB_UNC", "OMH_CHZ_LASER_SMB_UNC"))
    chz_laser_smb_username: str = Field(default="guest", validation_alias=AliasChoices("CHZ_LASER_SMB_USERNAME", "OMH_CHZ_LASER_SMB_USERNAME"))
    chz_laser_smb_password: str = Field(default="", validation_alias=AliasChoices("CHZ_LASER_SMB_PASSWORD", "OMH_CHZ_LASER_SMB_PASSWORD"))
    chz_laser_smb_require_signing: bool = Field(default=False, validation_alias=AliasChoices("CHZ_LASER_SMB_REQUIRE_SIGNING", "OMH_CHZ_LASER_SMB_REQUIRE_SIGNING"))
    chz_laser_smb_require_secure_negotiate: bool = Field(default=False, validation_alias=AliasChoices("CHZ_LASER_SMB_REQUIRE_SECURE_NEGOTIATE", "OMH_CHZ_LASER_SMB_REQUIRE_SECURE_NEGOTIATE"))
    chz_aggregation_onec_url: str = Field(default="", validation_alias=AliasChoices("CHZ_AGGREGATION_ONEC_URL", "OMH_CHZ_AGGREGATION_ONEC_URL"))
    chz_aggregation_onec_token: str = Field(default="", validation_alias=AliasChoices("CHZ_AGGREGATION_ONEC_TOKEN", "OMH_CHZ_AGGREGATION_ONEC_TOKEN"))
    chz_aggregation_onec_header_name: str = Field(default="X-OMH-Token", validation_alias=AliasChoices("CHZ_AGGREGATION_ONEC_HEADER_NAME", "OMH_CHZ_AGGREGATION_ONEC_HEADER_NAME"))
    chz_aggregation_onec_timeout_seconds: float = Field(default=180.0, validation_alias=AliasChoices("CHZ_AGGREGATION_ONEC_TIMEOUT_SECONDS", "OMH_CHZ_AGGREGATION_ONEC_TIMEOUT_SECONDS"))
    backup_dir: str = Field(default="", validation_alias=AliasChoices("BACKUP_DIR", "OMH_BACKUP_DIR"))
    health_checks_retention_days: float = Field(default=7.0, validation_alias=AliasChoices("HEALTH_CHECKS_RETENTION_DAYS", "OMH_HEALTH_CHECKS_RETENTION_DAYS"))
    retention_events_days: float = Field(default=30.0, validation_alias=AliasChoices("RETENTION_EVENTS_DAYS", "OMH_RETENTION_EVENTS_DAYS"))
    retention_artifacts_days: float = Field(default=30.0, validation_alias=AliasChoices("RETENTION_ARTIFACTS_DAYS", "OMH_RETENTION_ARTIFACTS_DAYS"))
    retention_artifacts_batch: int = Field(default=500, validation_alias=AliasChoices("RETENTION_ARTIFACTS_BATCH", "OMH_RETENTION_ARTIFACTS_BATCH"))
    federation_center_url: str = Field(default="", validation_alias=AliasChoices("FEDERATION_CENTER_URL", "OMH_FEDERATION_CENTER_URL"))
    federation_token: str = Field(default="", validation_alias=AliasChoices("FEDERATION_TOKEN", "OMH_FEDERATION_TOKEN"))
    federation_enabled: bool = Field(default=False, validation_alias=AliasChoices("FEDERATION_ENABLED", "OMH_FEDERATION_ENABLED"))
    federation_sync_interval_seconds: int = Field(default=300, validation_alias=AliasChoices("FEDERATION_SYNC_INTERVAL_SECONDS", "OMH_FEDERATION_SYNC_INTERVAL_SECONDS"))
    chz_dnp_packed_codes_export_url: str = Field(default="", validation_alias=AliasChoices("CHZ_DNP_PACKED_CODES_EXPORT_URL", "OMH_CHZ_DNP_PACKED_CODES_EXPORT_URL"))
    chz_dnp_packed_codes_timeout_seconds: float = Field(default=180.0, validation_alias=AliasChoices("CHZ_DNP_PACKED_CODES_TIMEOUT_SECONDS", "OMH_CHZ_DNP_PACKED_CODES_TIMEOUT_SECONDS"))
    require_worker_heartbeat: bool = Field(default=False, validation_alias=AliasChoices("OMH_REQUIRE_WORKER_HEARTBEAT", "REQUIRE_WORKER_HEARTBEAT"))
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
