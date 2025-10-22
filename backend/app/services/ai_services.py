import logging
from typing import List, Optional

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
    # 3️⃣ Generate response with fallback
    # =====================================================
    response_text = "Sorry, I couldn't generate a response."
    
    # Try Gemini first if selected
    if settings.AI_PROVIDER.lower() == "gemini":
        try:
            logger.info("💬 Trying Google Gemini model")
            genai.configure(api_key=settings.GEMINI_API_KEYS.split(",")[0])
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            result = model.generate_content(prompt)
            response_text = result.text.strip() if hasattr(result, "text") else str(result)
        except Exception as e:
            logger.warning(f"Gemini failed: {e}")
            # fallback to Cohere
            if cohere and settings.COHERE_API_KEY:
                try:
                    logger.info("💬 Falling back to Cohere model")
                    client = cohere.Client(settings.COHERE_API_KEY)
                    result = client.generate(
                        model="command-xlarge-nightly",
                        prompt=prompt,
                        max_tokens=400,
                        temperature=0.7,
                    )
                    response_text = result.generations[0].text.strip()
                except Exception as e2:
                    logger.error(f"Cohere fallback failed: {e2}")
    # If AI_PROVIDER is Cohere or Gemini failed entirely
    elif settings.AI_PROVIDER.lower() == "cohere" and cohere:
        try:
            logger.info("💬 Using Cohere model")
            client = cohere.Client(settings.COHERE_API_KEY)
            result = client.generate(
                model="command-xlarge-nightly",
                prompt=prompt,
                max_tokens=400,
                temperature=0.7,
            )
            response_text = result.generations[0].text.strip()
        except Exception as e:
            logger.error(f"Cohere generation failed: {e}")

    return response_text or "I'm not sure how to respond to that."


def summarize_text(text: str) -> str:
    """
    Summarize a given text using AI.
    """
    if not text:
        return "No content to summarize."

    prompt = f"Summarize this text clearly and concisely:\n\n{text}"
    # Try Gemini first, fallback to Cohere
    try:
        genai.configure(api_key=settings.GEMINI_API_KEYS.split(",")[0])
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        result = model.generate_content(prompt)
        return result.text.strip() if hasattr(result, "text") else str(result)
    except Exception as e:
        logger.warning(f"Gemini summarize failed: {e}")
        if cohere and settings.COHERE_API_KEY:
            try:
                client = cohere.Client(settings.COHERE_API_KEY)
                result = client.generate(
                    model="command-xlarge-nightly",
                    prompt=prompt,
                    max_tokens=400,
                    temperature=0.7,
                )
                return result.generations[0].text.strip()
            except Exception as e2:
                logger.error(f"Cohere summarize fallback failed: {e2}")
                return "Could not summarize the content at this time."
        return "Could not summarize the content at this time."
