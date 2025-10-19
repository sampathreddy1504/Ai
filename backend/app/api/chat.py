# backend/app/api/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.services.dialogue import manage_dialogue
from app.services.memory import save_chat_history

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: Optional[List[dict]] = None

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        reply = manage_dialogue(
            user_message=request.message,
            history=request.history,
            user_id=request.user_id
        )

        # Save to Redis short-term memory
        save_chat_history(request.user_id, request.message, reply)

        return ChatResponse(reply=reply)

    except Exception as e:
        logger.exception("Chat endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
