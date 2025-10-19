# backend/app/services/dialogue.py
import logging
from typing import List, Optional

from app.services import ai_services
from app.services.semantic_memory import query_semantic_memory, store_semantic_memory
from app.services.memory import get_all_user_facts, save_user_fact

logger = logging.getLogger(__name__)

def build_context_from_matches(matches: List[dict], max_chars: int = 800) -> str:
    pieces = []
    for m in matches:
        md = m.get("metadata", {})
        txt = md.get("text", "")
        score = m.get("score", None)
        pieces.append(f"- ({score:.3f}) {txt}" if score is not None else f"- {txt}")
    joined = "\n".join(pieces)
    if len(joined) > max_chars:
        joined = joined[:max_chars].rsplit("\n", 1)[0] + "\n[truncated]"
    return joined or "No similar conversations found."

def manage_dialogue(user_message: str, history: Optional[List[dict]] = None, user_id: Optional[str] = "anonymous") -> str:
    """
    Main conversation entrypoint:
    - Uses Pinecone for semantic memory
    - Loads Neo4j personalization facts
    - Stores new facts if detected (like "my name is ...")
    - Generates response using AI service
    """
    try:
        # 1️⃣ Get similar memory from Pinecone
        matches = query_semantic_memory(user_id=user_id, query=user_message, top_k=5)
        pinecone_context = build_context_from_matches(matches)

        # 2️⃣ Detect if user is telling their name
        if "my name is" in user_message.lower():
            name = user_message.split("my name is")[-1].strip().rstrip(".")
            save_user_fact(user_id, "name", name)

        # 3️⃣ Get all user facts from Neo4j
        user_facts = get_all_user_facts(user_id)

        # 4️⃣ Store current message in Pinecone
        try:
            if isinstance(user_message, str) and len(user_message) < 2000:
                store_semantic_memory(user_id=user_id, text=user_message, metadata={"source": "user_message"})
        except Exception:
            logger.exception("Failed to store semantic memory for message; continuing.")

        # 5️⃣ Generate a personalized response
        prompt = {"sender": user_id, "text": user_message}
        reply = ai_services.get_response(
            prompt,
            history=history,
            pinecone_context=pinecone_context,
            neo4j_facts=str(user_facts),
        )

        return reply

    except Exception as e:
        logger.exception("Dialogue management failed: %s", e)
        prompt = {"sender": user_id, "text": user_message}
        return ai_services.get_response(prompt, history=history)
