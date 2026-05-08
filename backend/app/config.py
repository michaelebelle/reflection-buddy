from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Reflection Buddy"
    debug: bool = False
    database_url: str = "sqlite:///./journal.db"

    # Future AI configuration — add keys here as features are built
    # openai_api_key: str | None = None
    # anthropic_api_key: str | None = None
    # embedding_model: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
