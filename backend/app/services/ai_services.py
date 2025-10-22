import time
import logging
from typing import List, Optional
from datetime import datetime

import google.generativeai as genai

try:
    import cohere
except ImportError:
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
    # 3️⃣ Try Cohere first, then fallback to Gemini
    # =====================================================
    response_text = ""
    cohere_failed = False

    # ----- Cohere Chat API -----
    if cohere:
        try:
            logger.info("💬 Using Cohere Chat API")
            client = cohere.Client(settings.COHERE_API_KEY)
            resp = client.chat(
                model="command-nightly",
                messages=[
                    {"role": "system", "content": MAIN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
            )
            response_text = getattr(resp, "message", "").strip()
            if not response_text:
                raise ValueError("Cohere response empty")
        except Exception as e:
            cohere_failed = True
            logger.warning(f"Cohere failed: {e}")

    # ----- Fallback to Google Gemini -----
    if cohere_failed or not response_text:
        try:
            logger.info("💬 Falling back to Google Gemini")
            genai.configure(api_key=settings.GEMINI_API_KEYS.split(",")[0])
            result = genai.GenerativeModel("gemini-1.5-pro-latest").generate_content(prompt)
            response_text = result.text.strip() if hasattr(result, "text") else str(result)
        except Exception as e:
            logger.error(f"Gemini failed: {e}")
            response_text = "Sorry, I couldn’t generate a response at this time."

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
