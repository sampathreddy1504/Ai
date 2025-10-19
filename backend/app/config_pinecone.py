# backend/app/config_pinecone.py
from pydantic_settings import BaseSettings
from pydantic import Field

class PineconeSettings(BaseSettings):
    PINECONE_API_KEY: str = Field(..., env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field(..., env="PINECONE_ENVIRONMENT")  # e.g., "us-east1"
    PINECONE_INDEX_NAME: str = Field("semantic-memory", env="PINECONE_INDEX_NAME")
    EMBEDDING_DIM: int = Field(384, env="EMBEDDING_DIM")  # match your embedding model

    class Config:
        extra = "ignore"  # ✅ ignore unrelated keys from .env
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a single instance for the app to use
pinecone_settings = PineconeSettings()
