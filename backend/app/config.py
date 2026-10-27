import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Hệ thống Quản lý Phòng Gym - HealthyGym"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:123@localhost:5432/healthygym"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "healthygym-super-secret-jwt-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
