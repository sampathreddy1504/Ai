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

# Configure Gemini once
genai.configure(api_key=settings.GEMINI_API_KEYS)
gemini_model = genai.GenerativeModel("gemini-pro")

def get_response(user_id: str, user_text: str, history: Optional[list] = None) -> str:
    """
    Generate AI response for a given user input.
    """
    from app.services.semantic_memory import query_semantic_memory, store_semantic_memory

    # Query and store semantic memory
    matches = query_semantic_memory(user_id, user_text, top_k=5)
    store_semantic_memory(user_id, user_text)

    context_text = "\n".join([m['content'] for m in matches]) if matches else ""

    # Add conversation context if available
    history_text = "\n".join([f"User: {h['user']}\nAI: {h['ai']}" for h in history]) if history else ""

    prompt = f"{MAIN_SYSTEM_PROMPT}\n{history_text}\nContext:\n{context_text}\nUser: {user_text}"

    try:
        if settings.AI_PROVIDER == "cohere" and cohere:
            client = cohere.Client(settings.COHERE_API_KEY)
            result = client.generate(model="command-xlarge-nightly", prompt=prompt, max_tokens=300)
            response_text = result.generations[0].text
        else:
            response = gemini_model.generate_content(prompt)
            response_text = response.text
        return response_text.strip()
    except Exception as e:
        logger.error(f"Error generating AI response: {e}", exc_info=True)
        return "⚠️ Sorry, something went wrong while generating a response."


def summarize_text(text: str) -> str:
    """
    Summarize a given text using AI.
    """
    prompt = f"Summarize the following text briefly:\n{text}"
    try:
        result = genai.generate(model="models/text-bison-001", prompt=prompt)
        return result.output_text
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        return "Could not summarize at this time."
