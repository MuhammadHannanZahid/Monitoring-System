from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = Field(..., alias="APP_NAME")
    app_version: str = Field(..., alias="APP_VERSION")
    app_env: str = Field(..., alias="APP_ENV")
    debug: bool = Field(..., alias="DEBUG")

    api_prefix: str = Field(..., alias="API_PREFIX")

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field(..., alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(..., alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(..., alias="REFRESH_TOKEN_EXPIRE_DAYS")

    mongo_uri: str = Field(..., alias="MONGO_URI")
    database_name: str = Field(..., alias="DATABASE_NAME")

    log_level: str = Field(..., alias="LOG_LEVEL")

    max_workers: int = Field(..., alias="MAX_WORKERS")
    default_timeout: int = Field(..., alias="DEFAULT_TIMEOUT")

    smtp_host: str = Field("", alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_user: str = Field("", alias="SMTP_USER")
    smtp_password: str = Field("", alias="SMTP_PASSWORD")

    default_admin_username: str
    default_admin_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()