import time
import logging
import json
from typing import List, Optional
from datetime import datetime

import google.generativeai as genai
try:
    import cohere
except Exception:
    cohere = None

from app.config import settings
from app.prompt_templates import MAIN_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# =====================================================
# AI Service Functions
# =====================================================

def get_response(message: dict, history: str = "", neo4j_facts: str = "") -> str:
    """
    Generate AI response for a given user input.
    message: dict with keys {sender: str(user_id), text: str}
    """
    from app.services.semantic_memory import query_semantic_memory, store_semantic_memory

    user_id = message.get("sender")
    user_text = message.get("text", "").strip()

    if not user_text:
        return "I didn’t catch that. Could you say it again?"

    # =====================================================
    # 1️⃣ Query & store semantic memory
    # =====================================================
    try:
        matches = query_semantic_memory(user_id, user_text, top_k=5)
    except Exception as e:
        logger.warning(f"Semantic memory query failed: {e}")
        matches = []

    try:
        store_semantic_memory(user_id, user_text)
    except Exception as e:
        logger.warning(f"Semantic memory store failed: {e}")

    # =====================================================
    # 2️⃣ Build context
    # =====================================================
    context_text = "\n".join([m["content"] for m in matches]) if matches else ""
    prompt = (
        f"{MAIN_SYSTEM_PROMPT}\n\n"
        f"=== User Context ===\n{context_text}\n\n"
        f"=== Knowledge Base Facts ===\n{neo4j_facts}\n\n"
        f"=== Chat History ===\n{history}\n\n"
        f"User: {user_text}\nAssistant:"
    )

    # =====================================================
    # 3️⃣ Choose AI provider
    # =====================================================
    response_text = ""
    try:
        if settings.AI_PROVIDER.lower() == "cohere" and cohere:
            logger.info("💬 Using Cohere model")
            client = cohere.Client(settings.COHERE_API_KEY)
            result = client.generate(
                model="command-xlarge-nightly",
                prompt=prompt,
                max_tokens=400,
                temperature=0.7,
            )
            response_text = result.generations[0].text.strip()
        else:
            logger.info("💬 Using Google Gemini model")
            genai.configure(api_key=settings.GEMINI_API_KEYS.split(",")[0])
            result = genai.GenerativeModel("gemini-1.5-pro-latest").generate_content(prompt)
            response_text = result.text.strip() if hasattr(result, "text") else str(result)
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        response_text = "Sorry, something went wrong while generating my response."

    # =====================================================
    # 4️⃣ Return final reply
    # =====================================================
    return response_text or "I'm not sure how to respond to that."


def summarize_text(text: str) -> str:
    """
    Summarize a given text using AI.
    """
    if not text:
        return "No content to summarize."

    prompt = f"Summarize this text clearly and concisely:\n\n{text}"
    try:
        genai.configure(api_key=settings.GEMINI_API_KEYS.split(",")[0])
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        result = model.generate_content(prompt)
        return result.text.strip() if hasattr(result, "text") else str(result)
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        return "Could not summarize the content at this time."
