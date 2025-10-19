# backend/app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # ====== AI Keys ======
    GEMINI_API_KEYS: str = Field(..., env="GEMINI_API_KEYS")  # Comma-separated
    COHERE_API_KEY: Optional[str] = Field(None, env="COHERE_API_KEY")
    GEMINI_MODEL: str = Field("gemini-2.5-flash", env="GEMINI_MODEL")

    # ====== Postgres ======
    POSTGRES_USER: str = Field("postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("postgres", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("personal_ai", env="POSTGRES_DB")
    POSTGRES_HOST: str = Field("db", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")

    # ====== Redis ======
    # Main Redis connection (some services use this default variable)
    REDIS_URL: Optional[str] = Field("redis://redis:6379/0", env="REDIS_URL")

    # Specific Redis URLs for subsystems
    REDIS_URL_CELERY: str = Field("redis://redis:6379/0", env="REDIS_URL_CELERY")  # For Celery
    REDIS_URL_CHAT: str = Field("redis://redis:6379/1", env="REDIS_URL_CHAT")      # For chat history
    REDIS_CHAT_HISTORY_KEY: str = Field("chat_history", env="REDIS_CHAT_HISTORY_KEY")  # last 10 messages

    # ====== Neo4j ======
    NEO4J_URI: str = Field("bolt://neo4j:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field("neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(..., env="NEO4J_PASSWORD")

    # ====== Email Settings ======
    EMAIL_USER: Optional[str] = Field(None, env="EMAIL_USER")
    EMAIL_PASS: Optional[str] = Field(None, env="EMAIL_PASS")

    # ====== Google OAuth ======
    GOOGLE_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")

    # ====== Backend ======
    PORT: int = Field(5000, env="PORT")
    DEBUG: bool = Field(True, env="DEBUG")

    # ====== AI Settings ======
    AI_PROVIDER_FAILURE_TIMEOUT: int = Field(30, env="AI_PROVIDER_FAILURE_TIMEOUT")

    # ====== Auth/JWT ======
    JWT_SECRET_KEY: str = Field("change_me_in_env", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_EXPIRES_MINUTES: int = Field(60 * 24 * 7, env="JWT_EXPIRES_MINUTES")  # default 7 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 👈 Ignores unexpected env vars like redis_url


# Instantiate settings
settings = Settings()
