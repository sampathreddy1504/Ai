from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import logging
import jwt
import json
import re
from typing import Optional

from app.services import ai_services, nlu
from app.db import utils as db_utils
from app.db.utils import (
    create_tables, save_chat, get_chat_history, get_conversations,
    get_messages_by_chat, delete_task, get_user_by_id
)
from app.db.neo4j_utils import save_fact_neo4j, get_facts_neo4j
from app.db.redis_utils import save_chat_redis, get_last_chats, get_redis_client
from app.config import settings
from app.api.auth import router as auth_router

app = FastAPI(title="Personal AI Assistant")
logger = logging.getLogger(__name__)

# ------------------- CORS -------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5000",
        "https://ai-9ddw.onrender.com",
        "https://ai-1-8ayp.onrender.com", 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- Startup -------------------
@app.on_event("startup")
async def startup_event():
    await run_in_threadpool(create_tables)
    logger.info("✅ Tables checked/created (tasks, chat_history)")

app.include_router(auth_router)

# ------------------- Helpers -------------------
def get_current_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

class ChatRequest(BaseModel):
    user_message: str
    token: str
    chat_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None

# ------------------- Root -------------------
@app.get("/")
async def root():
    return {"message": "🚀 Personal AI Assistant backend running!"}

# ------------------- Greet Endpoint -------------------
@app.get("/chat/greet")
async def greet(token: str, chat_id: Optional[str] = None):
    try:
        user_id = get_current_user_id(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_name, user_email = None, None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_name = payload.get("name")
        user_email = payload.get("email")
    except Exception:
        pass

    if not user_name:
        try:
            rec = await run_in_threadpool(get_user_by_id, user_id)
            user_name = rec.get("name") if rec else None
            user_email = rec.get("email") if rec else user_email
        except Exception:
            pass

    greeted = False
    try:
        redis = get_redis_client()
        greeting_key = f"greeted:{user_id}:daily"
        greeted = bool(redis.get(greeting_key))
        if not greeted:
            redis.set(greeting_key, "1", ex=24 * 60 * 60)
    except Exception:
        pass

    if greeted:
        return {"greeted": True, "message": None}

    message = f"Hello {user_name}! How's your day going? How can I assist you today?" if user_name else "Hello! How can I assist you today?"
    return {"greeted": False, "message": message}

# ------------------- Chat Endpoint -------------------
@app.post("/chat/")
async def chat(request: ChatRequest):
    user_message = request.user_message
    user_id = get_current_user_id(request.token)
    chat_id = request.chat_id

    logger.info(f"🔍 Chat request - user_id: {user_id}, chat_id: {chat_id}, message: {user_message[:50]}...")

    try:
        # ---------- Determine intent ----------
        structured = nlu.get_structured_intent(user_message)
        action = structured.get("action")

        # ---------- Quick greeting / identity ----------
        norm = user_message.lower().strip()
        greeting_match = bool(re.match(
            r'^\s*(?:hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
            norm, re.IGNORECASE
        ))

        name_queries = ["what is my name", "what's my name", "who am i", "do you know my name", "my name"]
        email_queries = ["what is my email", "what's my email", "what is my e-mail", "my email"]

        if greeting_match or any(q in norm for q in name_queries + email_queries):
            try:
                payload = jwt.decode(request.token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                name_from_token = payload.get("name")
                email_from_token = payload.get("email")
            except Exception:
                name_from_token = email_from_token = None

            if greeting_match:
                reply = f"Hello {name_from_token or 'there'}! How can I assist you today?"
            elif any(q in norm for q in name_queries):
                reply = f"Your name is {name_from_token}" if name_from_token else "I don't have your name yet."
            elif any(q in norm for q in email_queries):
                reply = f"Your email is {email_from_token}" if email_from_token else "I don't have your email yet."

            await run_in_threadpool(save_chat, user_id, user_message, reply, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, reply, chat_id)
            return {"success": True, "reply": reply, "intent": structured, "chat_id": chat_id}

        # ---------- Persist profile info ----------
        if request.user_name or request.user_email:
            await run_in_threadpool(db_utils.update_user_profile, user_id, request.user_name, request.user_email)

        # ---------- Build context ----------
        history_text = ""
        if chat_id:
            msgs = await run_in_threadpool(get_messages_by_chat, user_id, chat_id, 50)
            history_text = "\n".join([f"{'Human' if m['sender']=='user' else 'Assistant'}: {m['content']}" for m in msgs])
        else:
            extra_chats = await run_in_threadpool(get_chat_history, user_id, 10)
            history_text = "\n".join([f"Human: {c['user_query']}\nAssistant: {c['ai_response']}" for c in extra_chats])

        try:
            facts_list = await run_in_threadpool(get_facts_neo4j, user_id)
            facts_text = "\n".join([f"{fact['key']}: {fact['value']}" for fact in facts_list])
        except Exception as e:
            logger.warning(f"Neo4j fetch failed: {e}")
            facts_text = ""

        # ---------- Handle actions ----------
        if action == "general_chat":
            response = await run_in_threadpool(
                ai_services.get_response,
                user_message,
                history_text,
                facts_text
            )
            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, response, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, response, saved_chat_id)
            return {"success": True, "reply": response, "intent": structured, "chat_id": saved_chat_id}

        elif action == "create_task":
            task_data = structured.get("data", {})
            if not task_data.get("datetime"):
                # Ask for time
                await run_in_threadpool(db_utils.save_pending_task, user_id, task_data.get("title"))
                follow_up = f"When should I remind you for '{task_data.get('title')}'?"
                saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, follow_up, chat_id)
                await run_in_threadpool(save_chat_redis, user_id, user_message, follow_up, saved_chat_id)
                return {"success": True, "reply": follow_up, "status": "awaiting_time", "task": task_data, "chat_id": saved_chat_id}

            data_with_user = {**task_data, "user_id": user_id}
            await run_in_threadpool(db_utils.save_task, data_with_user)
            confirmation_message = f"Task saved: {task_data['title']} due {task_data['datetime']}"
            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, confirmation_message, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, confirmation_message, saved_chat_id)
            return {"success": True, "reply": confirmation_message, "status": "✅ Task saved", "task": task_data, "chat_id": saved_chat_id}

        elif action == "fetch_tasks":
            tasks = await run_in_threadpool(db_utils.get_tasks, user_id)
            reply = f"You have {len(tasks)} tasks."
            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, reply, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, reply, saved_chat_id)
            return {"success": True, "reply": reply, "tasks": tasks, "intent": structured}

        elif action == "save_fact":
            key = structured["data"]["key"]
            value = structured["data"]["value"]
            await run_in_threadpool(save_fact_neo4j, key, value)
            reply = f"I have saved the fact '{key}: {value}' in your knowledge base."
            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, reply, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, reply, saved_chat_id)
            return {"success": True, "reply": reply, "intent": structured}

        else:
            return {"success": False, "reply": "⚠ Unknown action", "intent": structured}

    except Exception as e:
        logger.exception(f"Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
