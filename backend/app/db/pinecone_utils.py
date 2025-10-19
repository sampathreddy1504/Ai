# backend/app/db/pinecone_utils.py
import logging
import traceback
from typing import Optional, List, Dict, Any
from pinecone import Pinecone, ServerlessSpec
from app.config_pinecone import pinecone_settings

logger = logging.getLogger(__name__)

_pc: Optional[Pinecone] = None
_index_name: str = pinecone_settings.PINECONE_INDEX_NAME
_region = "us-east-1"  # compatible free-tier region


def init_pinecone() -> Pinecone:
    """
    Initialize Pinecone client and ensure the target index exists.
    """
    global _pc
    if _pc:
        return _pc

    try:
        _pc = Pinecone(api_key=pinecone_settings.PINECONE_API_KEY)
        existing = _pc.list_indexes().names()

        if _index_name not in existing:
            logger.info(
                "Creating Pinecone index '%s' (dim=%d)...",
                _index_name,
                pinecone_settings.EMBEDDING_DIM,
            )
            _pc.create_index(
                name=_index_name,
                dimension=pinecone_settings.EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=_region),
            )

        logger.info("Pinecone ready. Index: %s", _index_name)
        return _pc

    except Exception as e:
        logger.error("Pinecone initialization failed: %s\n%s", e, traceback.format_exc())
        raise


def get_index():
    """
    Return a live handle to the Pinecone index.
    """
    global _pc
    if not _pc:
        init_pinecone()
    return _pc.Index(_index_name)


def upsert_vectors(items: List[Dict[str, Any]]) -> bool:
    """
    Upsert a batch of embeddings.
    Each item: {'id': str, 'values': [...], 'metadata': {...}}
    """
    try:
        idx = get_index()
        vectors = [(i["id"], i["values"], i.get("metadata", {})) for i in items]
        idx.upsert(vectors=vectors)
        return True
    except Exception as e:
        logger.error("Upsert failed: %s\n%s", e, traceback.format_exc())
        return False


def query_vectors(
    vector: List[float],
    top_k: int = 5,
    filter: Optional[Dict] = None,
    include_metadata: bool = True,
):
    """
    Query Pinecone for similar vectors.
    """
    try:
        idx = get_index()
        res = idx.query(
            vector=vector,
            top_k=top_k,
            filter=filter,
            include_metadata=include_metadata,
        )
        return res
    except Exception as e:
        logger.error("Query failed: %s\n%s", e, traceback.format_exc())
        return None
