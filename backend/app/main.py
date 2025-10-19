from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import logging
import jwt

from app.services import ai_services, nlu
from app.db import utils as db_utils
from app.db.utils import create_tables, save_chat, get_chat_history, get_conversations, get_messages_by_chat, delete_task, get_user_by_id  # correct import
from app.db.neo4j_utils import save_fact_neo4j, get_fact_neo4j, get_all_facts_for_user, get_facts_neo4j
from app.db.redis_utils import save_chat_redis, get_last_chats
from app.config import settings
from app.api.auth import router as auth_router
from app.db.redis_utils import get_redis_client

app = FastAPI(title="Personal AI Assistant")
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await run_in_threadpool(create_tables)
    logger.info("✅ Tables checked/created (tasks, chat_history)")

app.include_router(auth_router)


@app.get("/chat/greet")
async def greet(token: str, chat_id: str | None = None):
    """Return a personalized greeting for the authenticated user.
    This endpoint marks the greeting as served in Redis per chat_id so the same
    greeting isn't returned multiple times for the same conversation.
    """
    try:
        user_id = get_current_user_id(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Try to extract user info from token payload first (signup/login places name in token)
    user_name = None
    user_email = None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_name = payload.get("name") or None
        user_email = payload.get("email") or None
    except Exception:
        user_name = None
        user_email = None

    # If name not present in token, fallback to DB lookup
    if not user_name:
        try:
            user_record = await run_in_threadpool(get_user_by_id, user_id)
            user_name = user_record.get("name") if user_record else None
            if not user_email:
                user_email = user_record.get("email") if user_record else None
        except Exception:
            user_name = None
            user_email = None

    # Track greeting per-user globally (so user hears greeting once per day)
    greeted = False
    greeting_key = f"greeted:{user_id}:daily"
    try:
        redis = get_redis_client()
        greeted = bool(redis.get(greeting_key))
    except Exception:
        greeted = False

    if greeted:
        return {"greeted": True, "message": None}

    # Compose a friendly greeting
    if user_name:
        message = f"Hello {user_name}! How's your day going? How can I assist you today?"
    else:
        message = "Hello! How can I assist you today?"

    # Mark as greeted in Redis with a TTL (24 hours)
    try:
        if redis:
            redis.set(greeting_key, "1", ex=24 * 60 * 60)
    except Exception:
        pass

    return {"greeted": False, "message": message}

class ChatRequest(BaseModel):
    user_message: str
    token: str
    chat_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None
def get_current_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/")
async def root():
    return {"message": "🚀 Personal AI Assistant backend running!"}


@app.post("/debug/token")
async def debug_token(payload: dict):
    """Dev-only: POST {"token": "..."} returns decoded JWT payload or error."""
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return {"ok": True, "payload": decoded}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/debug/chat")
async def debug_chat(token: str, chat_id: str):
    """Dev-only: return persisted messages for chat_id as seen by get_messages_by_chat"""
    try:
        user_id = get_current_user_id(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        msgs = await run_in_threadpool(get_messages_by_chat, user_id, chat_id, 500)
        return {"ok": True, "user_id": user_id, "chat_id": chat_id, "messages": msgs}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/chat/")
async def chat(request: ChatRequest):
    user_message = request.user_message
    user_id = get_current_user_id(request.token)
    chat_id = request.chat_id
    
    print(f"🔍 Chat request - user_id: {user_id}, chat_id: {chat_id}, message: {user_message[:50]}...")
    
    try:
        # ---------- Determine intent ----------
        structured = nlu.get_structured_intent(user_message)
        action = structured.get("action")

        # Quick answers: if user asks about their name/email or just greets, prefer DB/token lookup
        try:
            norm = (user_message or "").lower().strip()
            import re

            # Greeting detection (user says hi/hello/...)
            greeting_match = bool(re.match(r'^\s*(?:hi|hello|hey|greetings|good morning|good afternoon|good evening)\b(?:\s+\S{1,30}){0,3}[,!.\-]*\s*', norm, re.IGNORECASE))

            name_queries = ["what is my name", "what's my name", "who am i", "do you know my name", "my name"]
            email_queries = ["what is my email", "what's my email", "what is my e-mail", "my email"]

            # If user greets, respond with a personalized greeting when possible
            if greeting_match:
                # try token payload first
                try:
                    payload = jwt.decode(request.token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    name_from_token = payload.get("name")
                except Exception:
                    name_from_token = None

                if name_from_token:
                    reply = f"Hello {name_from_token}! How can I assist you today?"
                else:
                    # fallback to DB
                    try:
                        rec = await run_in_threadpool(get_user_by_id, user_id)
                        uname = rec.get("name") if rec else None
                    except Exception:
                        uname = None
                    if uname:
                        reply = f"Hello {uname}! How can I assist you today?"
                    else:
                        reply = "Hello! I don't yet know your name — what should I call you?"

                # Save chat and return immediately
                await run_in_threadpool(save_chat, user_id, user_message, reply, chat_id)
                await run_in_threadpool(save_chat_redis, user_id, user_message, reply, chat_id)
                return {"success": True, "reply": reply, "intent": structured, "chat_id": chat_id}

        
            # Quick identity queries (name/email)
            
            if any(q in norm for q in name_queries):
                # try token payload first
                try:
                    payload = jwt.decode(request.token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    name_from_token = payload.get("name")
                except Exception:
                    name_from_token = None

                if name_from_token:
                    reply = f"Your name is {name_from_token}."
                else:
                    # fallback to DB
                    try:
                        rec = await run_in_threadpool(get_user_by_id, user_id)
                        uname = rec.get("name") if rec else None
                    except Exception:
                        uname = None
                    if uname:
                        reply = f"Your name is {uname}."
                    else:
                        reply = "I don't have your name yet. Would you like to tell me how I should call you?"

                # Save chat and return immediately
                await run_in_threadpool(save_chat, user_id, user_message, reply, chat_id)
                await run_in_threadpool(save_chat_redis, user_id, user_message, reply, chat_id)
                return {"success": True, "reply": reply, "intent": structured, "chat_id": chat_id}

            if any(q in norm for q in email_queries):
                try:
                    payload = jwt.decode(request.token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    email_from_token = payload.get("email")
                except Exception:
                    email_from_token = None

                if email_from_token:
                    reply = f"Your email is {email_from_token}."
                else:
                    try:
                        rec = await run_in_threadpool(get_user_by_id, user_id)
                        uemail = rec.get("email") if rec else None
                    except Exception:
                        uemail = None
                    if uemail:
                        reply = f"Your email is {uemail}."
                    else:
                        reply = "I don't have your email yet. Please provide it if you'd like notifications."

                await run_in_threadpool(save_chat, user_id, user_message, reply, chat_id)
                await run_in_threadpool(save_chat_redis, user_id, user_message, reply, chat_id)
                return {"success": True, "reply": reply, "intent": structured, "chat_id": chat_id}
        except Exception:
            # if any error in quick path, proceed to normal AI flow
            pass

        # Persist user profile info if provided (helps new users be recognized)
        try:
            if request.user_name or request.user_email:
                import logging
                logging.getLogger(__name__).info(f"Persisting profile for user {user_id}: name={request.user_name}, email={request.user_email}")
                await run_in_threadpool(db_utils.update_user_profile, user_id, request.user_name, request.user_email)
        except Exception as e:
            logging.getLogger(__name__).exception(f"Failed to persist profile for user {user_id}: {e}")

        # ---------- Fetch global context ----------
        # 1️⃣ Build history text from DB by chat_id if provided; fallback to recent chats
        history_text = ""
        if chat_id:
            msgs = await run_in_threadpool(get_messages_by_chat, user_id, chat_id, 50)
            history_text = "\n".join([f"{'Human' if m['sender']=='user' else 'Assistant'}: {m['content']}" for m in msgs])
        else:
            extra_chats = await run_in_threadpool(get_chat_history, user_id, 10)
            history_text = "\n".join([f"Human: {c['user_query']}\nAssistant: {c['ai_response']}" for c in extra_chats])

        # 3️⃣ Fetch all facts from Neo4j
        facts_list = await run_in_threadpool(get_facts_neo4j, user_id)
        facts_text = "\n".join([f"{fact['key']}: {fact['value']}" for fact in facts_list])

        # ---------- Handle actions ----------
        if action == "general_chat":
            # ✅ Wrap message in dict to avoid 'str' object has no attribute 'get'
            user_msg_dict = {"sender": str(user_id), "text": user_message}
            response = await run_in_threadpool(
                ai_services.get_response,
                user_msg_dict,
                history=history_text,
                neo4j_facts=facts_text
            )

            # Personalize reply with user name when appropriate:
            # Only prepend the user's name at the start of a conversation (no history)
            # and avoid duplicating the name if the AI reply already contains it.
            try:
                user_record = await run_in_threadpool(get_user_by_id, user_id)
                user_name = user_record.get("name") if user_record else None
                if user_name:
                    # Determine whether this is a truly new conversation by checking
                    # persisted messages for the provided chat_id. Relying on
                    # history_text.strip() can be brittle if history wasn't built.
                    try:
                        is_new_conversation = True
                        if chat_id:
                            msgs = await run_in_threadpool(get_messages_by_chat, user_id, chat_id, 1)
                            # If any persisted message exists for this chat_id,
                            # it's not a new conversation.
                            if msgs and len(msgs) > 0:
                                is_new_conversation = False
                        else:
                            # Fallback to previous behavior when no chat_id is provided
                            is_new_conversation = not history_text.strip()
                    except Exception:
                        # If anything fails, be conservative and assume not new
                        is_new_conversation = False

                    # Only personalize for new conversations
                    if is_new_conversation:
                        # Avoid double-prefixing if the AI already greets the user
                        # or already mentions their name in the opening chunk.
                        first_chunk = (response or "")[:200]
                        try:
                            import re
                            starts_with_greeting = bool(re.match(r"^\s*(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b", first_chunk, re.IGNORECASE))
                        except Exception:
                            starts_with_greeting = False

                        if not starts_with_greeting and user_name.lower() not in first_chunk.lower():
                            response = f"Hi {user_name}, {response}"
            except Exception:
                # If lookup fails, proceed without personalization
                pass

            # Ensure we correctly detect whether this chat has prior persisted messages
            try:
                is_new_conversation_check = True
                if chat_id:
                    msgs = await run_in_threadpool(get_messages_by_chat, user_id, chat_id, 1)
                    if msgs and len(msgs) > 0:
                        is_new_conversation_check = False
                else:
                    is_new_conversation_check = not bool(history_text.strip())
            except Exception:
                # conservative default: assume not new
                is_new_conversation_check = False

            # If this is NOT a new conversation, strip leading greetings from the AI response
            # to avoid the model greeting on every turn (the frontend also has a one-time greeting).
            if not is_new_conversation_check and response:
                try:
                    import re
                    # Safer regex: match leading greeting words and up to 3 short tokens after them
                    # Example matches: "Hello John, how are you?" -> "how are you?"
                    pattern = r'^\s*(?:hi|hello|hey|greetings|good morning|good afternoon|good evening)\b(?:\s+\S{1,30}){0,3}[,!.\-]*\s*'
                    stripped = re.sub(pattern, '', response, flags=re.IGNORECASE)
                    # Only replace if something meaningful remains; otherwise keep original
                    if stripped and stripped.strip():
                        response = stripped
                except Exception:
                    # If regex fails for any reason, keep original response
                    pass

            # Save chat for this user; ensure we get a canonical chat_id back
            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, response, chat_id)
            # propagate to redis and response
            await run_in_threadpool(save_chat_redis, user_id, user_message, response, saved_chat_id)

            return {"success": True, "reply": response, "intent": structured, "chat_id": saved_chat_id}

        elif action == "create_task":
            # If NLU didn't extract a datetime, ask a follow-up so we can schedule a reminder
            task_data = structured.get("data", {})
            if not task_data.get("datetime"):
                # Heuristic: if recent assistant message asked for time for a pending task,
                # treat the current user_message as the time and try to parse it.
                # Check for a saved pending task for this user and treat this message as the time
                pending = await run_in_threadpool(db_utils.get_pending_task, user_id)
                if pending:
                    # pending may be dict or tuple
                    pending_id = pending.get("id") if isinstance(pending, dict) else pending[0]
                    pending_title = pending.get("title") if isinstance(pending, dict) else pending[1]
                    from app.services import nlu as nlu_mod
                    parsed_time = nlu_mod.parse_time_string(user_message)
                    if parsed_time:
                        data_with_user = {"title": pending_title, "datetime": parsed_time, "priority": "medium", "category": "personal", "notes": "", "user_id": user_id}
                        await run_in_threadpool(db_utils.save_task, data_with_user)
                        # delete pending record
                        await run_in_threadpool(db_utils.delete_pending_task, pending_id)
                        confirmation_message = f"Task saved: {pending_title} due {parsed_time}"
                        saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, confirmation_message, chat_id)
                        await run_in_threadpool(save_chat_redis, user_id, user_message, confirmation_message, saved_chat_id)
                        return {"success": True, "reply": confirmation_message, "status": "✅ Task saved", "task": data_with_user}

                # Default: ask follow-up for datetime and save pending task
                follow_up = (
                    f"I can add the task '{task_data.get('title')}'. When should I remind you?"
                )
                # Save the pending task so a short follow-up can complete it
                await run_in_threadpool(db_utils.save_pending_task, user_id, task_data.get('title'))
                # Save the chat but don't create the DB task yet
                saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, follow_up, chat_id)
                await run_in_threadpool(save_chat_redis, user_id, user_message, follow_up, saved_chat_id)
                return {"success": True, "reply": follow_up, "status": "awaiting_time", "task": task_data, "chat_id": saved_chat_id}

            # attach user_id and persist
            data_with_user = {**task_data, "user_id": user_id}
            await run_in_threadpool(db_utils.save_task, data_with_user)
            confirmation_message = f"Task saved: {task_data['title']} due {task_data['datetime']}"

            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, confirmation_message, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, confirmation_message, saved_chat_id)

            return {"success": True, "reply": confirmation_message, "status": "✅ Task saved", "task": task_data, "chat_id": saved_chat_id}

        elif action == "fetch_tasks":
            tasks = await run_in_threadpool(db_utils.get_tasks, user_id)
            tasks_summary = f"You have {len(tasks)} tasks."

            # ✅ Wrap summary in dict for AI service
            tasks_msg_dict = {"sender": str(user_id), "text": tasks_summary}
            ai_reply = await run_in_threadpool(
                ai_services.get_response,
                tasks_msg_dict,
                history=history_text,
                neo4j_facts=facts_text
            )

            return {"success": True, "reply": ai_reply, "tasks": tasks, "intent": structured}

        elif action == "save_fact":
            key = structured["data"]["key"]
            value = structured["data"]["value"]
            await run_in_threadpool(save_fact_neo4j, key, value)

            confirmation_message = f"I have saved the fact '{key}: {value}' in your knowledge base."
            confirm_msg_dict = {"sender": str(user_id), "text": confirmation_message}  # ✅ wrapped
            ai_reply = await run_in_threadpool(
                ai_services.get_response,
                confirm_msg_dict,
                history=history_text,
                neo4j_facts=facts_text
            )

            return {"success": True, "reply": ai_reply, "intent": structured}
        elif action == "open_external":
            data = structured.get("data", {})
            target = (data.get("target") or "").lower()
            query = data.get("query") or ""

            # Build target URL
            from urllib.parse import quote_plus
            q = quote_plus(query)
            if target == "youtube":
                # If no query provided, open the YouTube homepage
                open_url = "https://www.youtube.com/" if not q else f"https://www.youtube.com/results?search_query={q}"
            elif target == "maps":
                open_url = "https://www.google.com/maps" if not q else f"https://www.google.com/maps/search/{q}"
            elif target == "whatsapp":
                # If no query, open web whatsapp; otherwise use wa.me with message
                open_url = "https://web.whatsapp.com/" if not q else f"https://wa.me/?text={q}"
            elif target == "spotify":
                # Spotify home if no query, else search
                open_url = "https://open.spotify.com/" if not q else f"https://open.spotify.com/search/{q}"
            elif target == "instagram":
                if not q:
                    open_url = "https://www.instagram.com/"
                else:
                    # Try profile or tag search. Use /explore/tags/ when query is multi-word
                    safe_q = q.replace('+', '%20')
                    open_url = f"https://www.instagram.com/explore/tags/{safe_q}/"
            else:
                open_url = None

            # Save the command like any other chat
            confirmation = f"Opening {target} for: {query}" if open_url else f"Could not open target: {target}"
            saved_chat_id = await run_in_threadpool(save_chat, user_id, user_message, confirmation, chat_id)
            await run_in_threadpool(save_chat_redis, user_id, user_message, confirmation, saved_chat_id)

            return {"success": True, "reply": confirmation, "intent": structured, "open_url": open_url, "chat_id": chat_id}

        elif action == "get_chat_history":
            # Return last 10 chats from Redis globally
            history = await run_in_threadpool(get_last_chats, user_id)
            return {"success": True, "history": history, "intent": structured}

        else:
            return {"success": False, "reply": "⚠ Unknown action", "intent": structured}

    except Exception as e:
        logger.exception(f"Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/api/tasks")
async def api_get_tasks(token: str):
    try:
        user_id = get_current_user_id(token)
        tasks = await run_in_threadpool(db_utils.get_tasks, user_id)
        formatted_tasks = [
            {
                "id": row["id"],
                "title": row["title"],
                "datetime": row["datetime"].isoformat() if row["datetime"] else None,
                "priority": row["priority"],
                "category": row["category"],
                "notes": row["notes"],
                "notified": row["notified"]
            }
            for row in tasks
        ]
        return {"success": True, "tasks": formatted_tasks}
    except Exception as e:
        logger.exception(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")


@app.delete("/api/tasks/{task_id}")
async def api_delete_task(task_id: int, token: str):
    try:
        user_id = get_current_user_id(token)
        success = await run_in_threadpool(delete_task, user_id, task_id)
        if success:
            return {"success": True, "message": "Task deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        logger.exception(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete task")


@app.delete("/api/tasks/clear_completed")
async def api_clear_completed(payload: dict | None = Body(None), token: str | None = None):
    """Delete all completed (notified) tasks for the authenticated user.
    Accepts either query param token or JSON body { token: '...' } from frontend.
    """
    # token may be provided either as query param or in JSON body
    t = token or (payload.get("token") if payload else None)
    if not t:
        raise HTTPException(status_code=400, detail="token required")
    try:
        user_id = get_current_user_id(t)
        logger.info(f"Clearing completed tasks for user {user_id}")
        success = await run_in_threadpool(db_utils.delete_completed_tasks, user_id)
        if success:
            return {"success": True, "deleted": True}
        else:
            return {"success": True, "deleted": False}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error clearing completed tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear completed tasks")


@app.patch("/api/tasks/{task_id}/status")
async def api_update_task_status(task_id: int, token: str, status: str):
    """Toggle or set task status. status should be 'completed' or 'pending'.
    We map 'completed' to notified = TRUE, 'pending' to FALSE.
    """
    if status not in ("completed", "pending"):
        raise HTTPException(status_code=400, detail="invalid status")
    try:
        user_id = get_current_user_id(token)
        notified = True if status == "completed" else False
        success = await run_in_threadpool(db_utils.set_task_notified, user_id, task_id, notified)
        if success:
            return {"success": True, "task_id": task_id, "notified": notified}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task status")


@app.get("/api/conversations")
async def api_get_conversations(token: str):
    try:
        user_id = get_current_user_id(token)
        convos = await run_in_threadpool(get_conversations, user_id)
        return {"success": True, "conversations": convos}
    except Exception as e:
        logger.exception(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch conversations")


@app.get("/api/conversations/{chat_id}")
async def api_get_messages(chat_id: str, token: str):
    try:
        user_id = get_current_user_id(token)
        messages = await run_in_threadpool(get_messages_by_chat, user_id, chat_id, 500)
        return {"success": True, "messages": messages}
    except Exception as e:
        logger.exception(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@app.post("/chat-with-upload/")
async def chat_with_upload(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    token: str = Form(...),
    chat_id: str | None = Form(default=None)
):
    try:
        user_id = get_current_user_id(token)

        # Parse prompt JSON {"sender": ..., "text": ...}
        try:
            import json
            prompt_obj = json.loads(prompt) if isinstance(prompt, str) else prompt
            user_text = prompt_obj.get("text") if isinstance(prompt_obj, dict) else str(prompt)
        except Exception:
            user_text = str(prompt)

        # We don't process the file contents in this stub; ensure read to avoid warnings
        await file.read()  # discard

        # Create a simple response using AI service context if available
        user_msg_dict = {"sender": str(user_id), "text": user_text}
        ai_reply = await run_in_threadpool(
            ai_services.get_response,
            user_msg_dict,
            history="",
            neo4j_facts=""
        )

        # Save entries
        await run_in_threadpool(save_chat, user_id, user_text, ai_reply, chat_id)
        await run_in_threadpool(save_chat_redis, user_id, user_text, ai_reply, chat_id)

        return {"success": True, "response": ai_reply}
    except Exception as e:
        logger.exception(f"Upload chat failed: {e}")
        raise HTTPException(status_code=500, detail="Upload chat failed")