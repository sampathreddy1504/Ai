from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import logging
import jwt

from app.services import ai_services, nlu
from app.db import utils as db_utils
from app.db.utils import (
    create_tables,
    save_chat,
    get_chat_history,
    get_conversations,
    get_messages_by_chat,
    delete_task,
    get_user_by_id,
)
from app.db.neo4j_utils import save_fact_neo4j, get_facts_neo4j
from app.db.redis_utils import save_chat_redis, get_last_chats, get_redis_client
from app.config import settings
from app.api.auth import router as auth_router

logger = logging.getLogger(__name__)
app = FastAPI(title="Personal AI Assistant")

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-4-w41p.onrender.com"  # deployed frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Startup --------------------
@app.on_event("startup")
async def startup_event():
    await run_in_threadpool(create_tables)
    logger.info("✅ Tables checked/created (tasks, chat_history)")

# -------------------- Include Routers --------------------
app.include_router(auth_router)

# -------------------- Models --------------------
class ChatRequest(BaseModel):
    user_message: str
    token: str
    chat_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None

# -------------------- Helper --------------------
def get_current_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# -------------------- Routes --------------------
@app.get("/")
async def root():
    return {"message": "🚀 Personal AI Assistant backend running!"}

@app.get("/chat/greet")
async def greet(token: str, chat_id: str | None = None):
    """Personalized greeting."""
    try:
        user_id = get_current_user_id(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_name = None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_name = payload.get("name")
    except Exception:
        pass

    if not user_name:
        try:
            user_record = await run_in_threadpool(get_user_by_id, user_id)
            user_name = user_record.get("name") if user_record else None
        except Exception:
            pass

    greeted = False
    try:
        redis = get_redis_client()
        greeted = bool(redis.get(f"greeted:{user_id}:daily"))
    except Exception:
        pass

    if greeted:
        return {"greeted": True, "message": None}

    message = f"Hello {user_name}! How's your day going? How can I assist you today?" if user_name else "Hello! How can I assist you today?"

    try:
        if redis:
            redis.set(f"greeted:{user_id}:daily", "1", ex=24*60*60)
    except Exception:
        pass

    return {"greeted": False, "message": message}

# -------------------- Chat --------------------
@app.post("/chat/")
async def chat(request: ChatRequest):
    user_message = request.user_message
    user_id = get_current_user_id(request.token)
    chat_id = request.chat_id

    print(f"🔍 Chat request - user_id: {user_id}, chat_id: {chat_id}, message: {user_message[:50]}...")

    try:
        # NLU
        structured = nlu.get_structured_intent(user_message)
        action = structured.get("action")

        # Quick greetings / identity queries
        import re
        norm = user_message.lower().strip()
        greeting_match = bool(re.match(r'^\s*(?:hi|hello|hey|greetings|good morning|good afternoon|good evening)\b', norm))
        name_queries = ["what is my name", "what's my name", "who am i", "do you know my name", "my name"]
        email_queries = ["what is my email", "what's my email", "my email"]

        if greeting_match or any(q in norm for q in name_queries + email_queries):
            reply = None
            # Token payload
            try:
                payload = jwt.decode(request.token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                name_from_token = payload.get("name")
                email_from_token = payload.get("email")
            except Exception:
                name_from_token = email_from_token = None

            # Fallback DB
            try:
                user_record = await run_in_threadpool(get_user_by_id, user_id)
                uname = user_record.get("name") if user_record else None
                uemail = user_record.get("email") if user_record else None
            except Exception:
                uname = uemail = None

            if greeting_match:
                reply = f"Hello {name_from_token or uname or ''}! How can I assist you today?"
            elif any(q in norm for q in name_queries):
                reply = f"Your name is {name_from_token or uname or 'unknown'}."
            elif any(q in norm for q in email_queries):
                reply = f"Your email is {email_from_token or uemail or 'unknown'}."

            await run_in_threadpool(save_chat, user_id, user_message, reply, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, reply, chat_id)
            return {"success": True, "reply": reply, "intent": structured, "chat_id": chat_id}

        # Persist profile
        if request.user_name or request.user_email:
            await run_in_threadpool(db_utils.update_user_profile, user_id, request.user_name, request.user_email)

        # Build history
        history_text = ""
        if chat_id:
            msgs = await run_in_threadpool(get_messages_by_chat, user_id, chat_id, 50)
            history_text = "\n".join([f"{'Human' if m['sender']=='user' else 'Assistant'}: {m['content']}" for m in msgs])
        else:
            extra_chats = await run_in_threadpool(get_chat_history, user_id, 10)
            history_text = "\n".join([f"Human: {c['user_query']}\nAssistant: {c['ai_response']}" for c in extra_chats])

        # Fetch facts
        facts_list = await run_in_threadpool(get_facts_neo4j, user_id)
        facts_text = "\n".join([f"{fact['key']}: {fact['value']}" for fact in facts_list])

        # Handle general chat
        if action == "general_chat":
            user_msg_dict = {"sender": str(user_id), "text": user_message}
            response = await run_in_threadpool(ai_services.get_response, user_msg_dict, history=history_text, neo4j_facts=facts_text)

            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, response, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, response, saved_chat_id)

            return {"success": True, "reply": response, "intent": structured, "chat_id": saved_chat_id}

        # Add other actions (create_task, fetch_tasks, save_fact, open_external) as needed
        return {"success": False, "reply": "⚠ Unknown action", "intent": structured}

    except Exception as e:
        logger.exception(f"Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# -------------------- Chat with Upload --------------------
@app.post("/chat-with-upload/")
async def chat_with_upload(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    token: str = Form(...),
    chat_id: str | None = Form(default=None)
):
    try:
        user_id = get_current_user_id(token)
        import json
        prompt_obj = json.loads(prompt) if isinstance(prompt, str) else prompt
        user_text = prompt_obj.get("text") if isinstance(prompt_obj, dict) else str(prompt)
        await file.read()  # discard

        user_msg_dict = {"sender": str(user_id), "text": user_text}
        ai_reply = await run_in_threadpool(ai_services.get_response, user_msg_dict, history="", neo4j_facts="")

        await run_in_threadpool(save_chat, user_id, user_text, ai_reply, chat_id)
        await run_in_threadpool(save_chat_redis, user_id, user_text, ai_reply, chat_id)

        return {"success": True, "response": ai_reply}
    except Exception as e:
        logger.exception(f"Upload chat failed: {e}")
        raise HTTPException(status_code=500, detail="Upload chat failed")
