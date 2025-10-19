# backend/app/db/pinecone_chat.py
import logging
import uuid
from typing import List, Dict
from app.db.pinecone_utils import upsert_vectors, query_vectors, init_pinecone
import traceback

logger = logging.getLogger(__name__)

# Ensure Pinecone client is initialized
init_pinecone()


def store_message_in_pinecone(user_id: str, message_text: str, embedding: List[float]) -> bool:
    """
    Stores a single user message in Pinecone for context retrieval.
    """
    try:
        message_id = f"{user_id}_{uuid.uuid4()}"
        item = {
            "id": message_id,
            "values": embedding,
            "metadata": {"user_id": user_id, "text": message_text},
        }

        success = upsert_vectors([item])
        if not success:
            logger.error("Failed to upsert message into Pinecone")
            return False

        logger.info("Stored message in Pinecone: %s", message_id)
        return True

    except Exception as e:
        logger.error("Error storing message in Pinecone: %s\n%s", e, traceback.format_exc())
        return False


def retrieve_context(user_id: str, embedding: List[float], top_k: int = 5) -> List[Dict]:
    """
    Retrieves relevant context messages from Pinecone for a user.
    """
    try:
        init_pinecone()  # Ensure Pinecone is initialized

        filter_metadata = {"user_id": user_id}
        result = query_vectors(
            vector=embedding,
            top_k=top_k,
            filter=filter_metadata,
            include_metadata=True,
        )

        if not result or "matches" not in result:
            return []

        return [match["metadata"] for match in result["matches"]]

    except Exception as e:
        logger.error("Error retrieving context from Pinecone: %s\n%s", e, traceback.format_exc())
        return []
