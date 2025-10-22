# backend/app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn
from typing import Optional

class Settings(BaseSettings):
    # ====== AI Keys ======
    AI_PROVIDER: str = Field("gemini", env="AI_PROVIDER")
    AI_PROVIDER_FAILURE_TIMEOUT: int = Field(30, env="AI_PROVIDER_FAILURE_TIMEOUT")
    GEMINI_API_KEYS: str = Field(..., env="GEMINI_API_KEYS")  # Comma-separated if multiple
    GEMINI_MODEL: str = Field("gemini-2.5-flash", env="GEMINI_MODEL")
    COHERE_API_KEY: Optional[str] = Field(None, env="COHERE_API_KEY")
    EMBEDDING_DIM: int = Field(384, env="EMBEDDING_DIM")

    # ====== Database ======
    DATABASE_URL: Optional[PostgresDsn] = Field(None, env="DATABASE_URL")
    POSTGRES_USER: Optional[str] = Field(None, env="POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = Field(None, env="POSTGRES_PASSWORD")
    POSTGRES_DB: Optional[str] = Field(None, env="POSTGRES_DB")
    POSTGRES_HOST: Optional[str] = Field(None, env="POSTGRES_HOST")
    POSTGRES_PORT: Optional[int] = Field(None, env="POSTGRES_PORT")

    # ====== Redis ======
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")  # Default Redis
    REDIS_URL_CELERY: Optional[str] = Field(None, env="REDIS_URL_CELERY")
    REDIS_URL_CHAT: Optional[str] = Field(None, env="REDIS_URL_CHAT")
    REDIS_CHAT_HISTORY_KEY: str = Field("chat_history", env="REDIS_CHAT_HISTORY_KEY")

    # ====== Neo4j ======
    NEO4J_URI: str = Field(..., env="NEO4J_URI")
    NEO4J_USER: str = Field(..., env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(..., env="NEO4J_PASSWORD")

    # ====== Email ======
    EMAIL_USER: Optional[str] = Field(None, env="EMAIL_USER")
    EMAIL_PASS: Optional[str] = Field(None, env="EMAIL_PASS")

    # ====== Google OAuth ======
    GOOGLE_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")

    # ====== Backend ======
    PORT: int = Field(5000, env="PORT")
    DEBUG: bool = Field(True, env="DEBUG")

    # ====== Auth/JWT ======
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_EXPIRES_MINUTES: int = Field(60 * 24 * 7, env="JWT_EXPIRES_MINUTES")  # default 7 days

    # ====== Pinecone ======
    PINECONE_API_KEY: Optional[str] = Field(None, env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: Optional[str] = Field(None, env="PINECONE_INDEX_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unexpected env vars

# Instantiate settings
settings = Settings()

# Optional: if DATABASE_URL is provided, parse it to individual Postgres fields
if settings.DATABASE_URL:
    from urllib.parse import urlparse
    url = urlparse(settings.DATABASE_URL)
    settings.POSTGRES_USER = url.username
    settings.POSTGRES_PASSWORD = url.password
    settings.POSTGRES_DB = url.path[1:]  # strip leading /
    settings.POSTGRES_HOST = url.hostname
    settings.POSTGRES_PORT = url.port
