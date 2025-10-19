# backend/app/services/embeddings.py
"""
Embedding utility. Primary method: local sentence-transformers model 'all-MiniLM-L6-v2'.
Fallback: Cohere (if configured) embeddings.
This module exposes get_embedding(text: str) -> List[float] and get_batch_embeddings(list[str]).
"""

import logging
import os
from typing import List
logger = logging.getLogger(__name__)

# Try local sentence-transformers first (recommended for 'all-MiniLM-L6-v2')
try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_MODEL_NAME = os.getenv("SENTENCE_MODEL_NAME", "all-MiniLM-L6-v2")
    _s_model = SentenceTransformer(_SENTENCE_MODEL_NAME)
    logger.info("Loaded local SentenceTransformer model: %s", _SENTENCE_MODEL_NAME)

    def get_embedding(text: str) -> List[float]:
        vec = _s_model.encode(text, show_progress_bar=False, convert_to_numpy=True)
        return vec.tolist()

    def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
        vecs = _s_model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return [v.tolist() for v in vecs]

except Exception as e:
    logger.warning("SentenceTransformers not available or failed to load: %s. Falling back to Cohere if available.", e)
    _s_model = None

    # fallback to Cohere if cohere client exists
    try:
        from app.services.ai_services import cohere_client
        if cohere_client is None:
            raise RuntimeError("Cohere client not configured")
        def get_embedding(text: str):
            resp = cohere_client.embed(texts=[text], model="embed-english-v2.0")
            return resp.embeddings[0]

        def get_batch_embeddings(texts: List[str]):
            resp = cohere_client.embed(texts=texts, model="embed-english-v2.0")
            return resp.embeddings
        logger.info("Using Cohere embeddings as fallback.")
    except Exception as ex:
        logger.error("No embedding provider available. Install sentence-transformers or configure Cohere. %s", ex)
        def get_embedding(text: str):
            raise RuntimeError("No embedding provider available. Install sentence-transformers or configure Cohere.")

        def get_batch_embeddings(texts: List[str]):
            raise RuntimeError("No embedding provider available. Install sentence-transformers or configure Cohere.")
