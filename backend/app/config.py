from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Reflection Buddy"
    debug: bool = False
    database_url: str = "sqlite:///./journal.db"

    # Auth — set SECRET_KEY to a long random string in production.
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "dev-secret-change-me-in-production"
    # Long expiry so friends testing don't get logged out constantly.
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Audit trail — kept for backwards compatibility; superseded by JWT user identity.
    journal_owner: str = "owner"

    # Future AI configuration — add keys here as features are built
    # openai_api_key: str | None = None
    # anthropic_api_key: str | None = None
    # embedding_model: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
