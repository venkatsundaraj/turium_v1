from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME:str = "AI Knowledge Inbox"
    DATABASE_URL:str = ""
    OPENAI_API_KEY:str = ""
    ANTHROPIC_API_KEY:str = ""

    CHAT_MODEL:str = "gpt-5-mini"
    CORS_ORIGINS:list[str] = ["http://localhost:3000"]
    LOG_LEVEL:str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding = "utf-8"
    )

    @property
    def sqlalchemy_url(self)->str:
        """One driver (psycopg 3) for both the async app engine and sync Alembic."""
        return make_url(self.DATABASE_URL).set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


@lru_cache
def get_settings()->Settings:
    return Settings()

settings = get_settings()
