from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./engine.db"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    STAGEHAND_ENABLED: bool = False
    STAGEHAND_MOCK: bool = True
    OPENROUTER_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
