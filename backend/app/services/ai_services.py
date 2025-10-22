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

def get_response(
    user_id: str,
    user_text: str,
    model: str = "gemini",
    history: Optional[List[dict]] = None
):
    """
    Generate AI response for a given user input.
    """
    from app.services.semantic_memory import query_semantic_memory, store_semantic_memory

    # Query semantic memory for context
    matches = query_semantic_memory(user_id, user_text, top_k=5)

    # Store user's input
    store_semantic_memory(user_id, user_text)

    # Combine previous messages (if any)
    history_text = ""
    if history:
        for h in history[-5:]:  # limit to last few messages
            history_text += f"{h['role']}: {h['content']}\n"

    # Build AI prompt
    context_text = "\n".join([m['content'] for m in matches]) if matches else ""
    prompt = (
        f"{MAIN_SYSTEM_PROMPT}\n\n"
        f"Chat History:\n{history_text}\n"
        f"Context:\n{context_text}\n\n"
        f"User: {user_text}\nAssistant:"
    )

    response_text = ""
    try:
        if settings.AI_PROVIDER.lower() == "cohere" and cohere:
            client = cohere.Client(settings.COHERE_API_KEY)
            result = client.generate(model="command", prompt=prompt, max_tokens=400)
            response_text = result.generations[0].text.strip()
        else:
            genai.configure(api_key=settings.GEMINI_API_KEYS.split(",")[0])
            model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"
            result = genai.GenerativeModel(model_name).generate_content(prompt)
            response_text = result.text.strip()
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        response_text = "Sorry, something went wrong while generating a response."

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
