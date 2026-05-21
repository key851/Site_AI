from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Нормативное обеспечение ИИ в РФ"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/ai_norms"
    debug: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()