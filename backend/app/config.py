import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "VyaparSetu"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./vyaparsetu.db"

    # Security & JWT
    SECRET_KEY: str = "vyaparsetu-bharatcode-dev-secret-key-32chars-minimum-hash"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # BharatCode Hosted LLM
    BHARATCODE_API_KEY: str = "test_bharatcode_key"
    BHARATCODE_BASE_URL: str = "https://bharatcode.ai/api/model/v1"
    BHARATCODE_MODEL_NAME: str = "qwen-3.8-27b"
    AI_MODE: str = "DEV_SIMULATION"  # "PRODUCTION_BHARATCODE" or "DEV_SIMULATION"
    AI_PROVIDER_LABEL: str = "BharatCode Qwen 3.8 27B"

    # Storage
    STORAGE_DIR: str = str(BASE_DIR / "backend" / "storage")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

