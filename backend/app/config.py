# backend/app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from urllib.parse import urlparse

class Settings(BaseSettings):
    # ====== AI Keys ======
    GEMINI_API_KEYS: str = Field(..., env="GEMINI_API_KEYS")
    COHERE_API_KEY: Optional[str] = Field(None, env="COHERE_API_KEY")
    GEMINI_MODEL: str = Field("gemini-2.5-flash", env="GEMINI_MODEL")
    AI_PROVIDER: str = Field("gemini", env="AI_PROVIDER")
    AI_PROVIDER_FAILURE_TIMEOUT: int = Field(30, env="AI_PROVIDER_FAILURE_TIMEOUT")

    # ====== Postgres ======
    DATABASE_URL: str = Field(..., env="DATABASE_URL")  # plain string for urlparse
    # Optional individual fields if you still want them
    POSTGRES_USER: Optional[str] = Field(None, env="POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = Field(None, env="POSTGRES_PASSWORD")
    POSTGRES_DB: Optional[str] = Field(None, env="POSTGRES_DB")
    POSTGRES_HOST: Optional[str] = Field(None, env="POSTGRES_HOST")
    POSTGRES_PORT: Optional[int] = Field(5432, env="POSTGRES_PORT")

    # ====== Redis ======
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")  # fallback
    REDIS_URL_CELERY: str = Field(..., env="REDIS_URL_CELERY")
    REDIS_URL_CHAT: str = Field(..., env="REDIS_URL_CHAT")
    REDIS_CHAT_HISTORY_KEY: str = Field("chat_history", env="REDIS_CHAT_HISTORY_KEY")

    # ====== Neo4j ======
    NEO4J_URI: str = Field(..., env="NEO4J_URI")
    NEO4J_USER: str = Field(..., env="NEO4J_USER")
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

    # ====== JWT ======
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_EXPIRES_MINUTES: int = Field(60 * 24 * 7, env="JWT_EXPIRES_MINUTES")

    # ====== Pinecone ======
    PINECONE_API_KEY: Optional[str] = Field(None, env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: Optional[str] = Field(None, env="PINECONE_INDEX_NAME")

    # ====== Embeddings ======
    EMBEDDING_DIM: int = Field(384, env="EMBEDDING_DIM")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore unexpected env vars

# Instantiate settings
settings = Settings()

# Parse DATABASE_URL safely
from urllib.parse import urlparse
db_url = urlparse(settings.DATABASE_URL)  # ✅ cast to string handled
