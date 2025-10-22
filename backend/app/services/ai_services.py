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

def get_response(message: str, model: str = "gemini", history=None):
    # Your logic

    """
    Generate AI response for a given user input.
    """
    # Local import to prevent circular import
    from app.services.semantic_memory import query_semantic_memory, store_semantic_memory

    # Query semantic memory
    matches = query_semantic_memory(user_id, user_text, top_k=5)

    # Store the user's input
    store_semantic_memory(user_id, user_text)

    # Build context for AI
    context_text = "\n".join([m['content'] for m in matches]) if matches else ""
    prompt = f"{MAIN_SYSTEM_PROMPT}\nContext:\n{context_text}\nUser: {user_text}"

    # Choose provider
    response_text = ""
    try:
        if settings.AI_PROVIDER == "cohere" and cohere:
            client = cohere.Client(settings.COHERE_API_KEY)
            result = client.generate(model="xlarge", prompt=prompt, max_tokens=300)
            response_text = result.text
        else:
            result = genai.generate(model="models/text-bison-001", prompt=prompt)
            response_text = result.output_text
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        response_text = "Sorry, something went wrong."

    return response_text


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
