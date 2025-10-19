# backend/app/services/semantic_memory.py
import uuid
import time
import logging
from typing import List, Dict, Any, Optional

from app.db.pinecone_utils import upsert_vectors, query_vectors, init_pinecone
from app.services.embeddings import get_embedding, get_batch_embeddings

logger = logging.getLogger(__name__)

# Ensure Pinecone client/Index is initialized once at import
try:
    init_pinecone()
except Exception as e:
    logger.error("Pinecone init failed at import: %s", e)


def store_semantic_memory(
    user_id: str,
    text: str,
    namespace: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Store one text entry with embedding for user.
    """
    try:
        vec = get_embedding(text)
        item_id = f"{user_id}-{uuid.uuid4()}"
        meta = dict(metadata or {})
        meta.update({"user_id": user_id, "text": text, "stored_at": int(time.time())})
        ok = upsert_vectors([{"id": item_id, "values": vec, "metadata": meta}])
        return {"ok": ok, "id": item_id}
    except Exception as e:
        logger.error("store_semantic_memory failed: %s", e)
        return {"ok": False, "error": str(e)}


def store_many(
    user_id: str, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Batch store multiple text entries.
    """
    try:
        if not texts:
            return {"ok": True, "stored": 0}
        if metadatas is None:
            metadatas = [{} for _ in texts]
        embeddings = get_batch_embeddings(texts)
        items = []
        now = int(time.time())
        for i, emb in enumerate(embeddings):
            meta = dict(metadatas[i]) if i < len(metadatas) else {}
            meta.update({"user_id": user_id, "text": texts[i], "stored_at": now})
            items.append(
                {"id": f"{user_id}-{uuid.uuid4()}", "values": emb, "metadata": meta}
            )
        ok = upsert_vectors(items)
        return {"ok": ok, "stored": len(items)}
    except Exception as e:
        logger.error("store_many failed: %s", e)
        return {"ok": False, "error": str(e)}


def query_semantic_memory(
    user_id: str, query: str, top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Query Pinecone for semantically similar past messages.
    Returns list of {'id':..., 'score':..., 'metadata':{...}}.
    """
    try:
        vec = get_embedding(query)
        filter_obj = {"user_id": {"$eq": user_id}}
        res = query_vectors(vector=vec, top_k=top_k, filter=filter_obj)
        if not res:
            return []

        # Normalize Pinecone results
        matches = []
        raw = getattr(res, "matches", None) or res.get("matches", [])
        for m in raw:
            matches.append(
                {
                    "id": getattr(m, "id", None) or m.get("id"),
                    "score": getattr(m, "score", None) or m.get("score"),
                    "metadata": getattr(m, "metadata", None) or m.get("metadata", {}),
                }
            )
        return matches
    except Exception as e:
        logger.error("query_semantic_memory failed: %s", e)
        return []
