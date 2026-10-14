
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root: StockAnalyzeAgent/
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    twelve_data_api_key: str
    news_api_key: str
    gemini_api_key: str
    gemini_model: str = "gemini-3.8-flash"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
