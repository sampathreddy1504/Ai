# app/db/redis_utils.py
from app.config import settings
import redis
import json

# Initialize Redis client safely
def get_redis_client():
    """
    Returns a Redis client or None if connection fails.
    """
    try:
        client = redis.Redis.from_url(settings.REDIS_URL_CHAT, decode_responses=True)
        client.ping()  # Test connection
        return client
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        return None

def _user_key(user_id: int, chat_id: str | None = None) -> str:
    """
    Build Redis key for user chat history. Uses optional chat_id.
    """
    chat_suffix = chat_id or "default"
    return f"{settings.REDIS_CHAT_HISTORY_KEY}:{user_id}:{chat_suffix}"

def save_chat_redis(user_id: int, user_message: str, bot_reply: str, chat_id: str | None = None):
    """
    Save a chat entry to Redis. Keeps last 10 messages per user per chat.
    """
    client = get_redis_client()
    if not client:
        return  # Skip saving if Redis is down

    chat_entry = {"chat_id": chat_id, "user": user_message, "bot": bot_reply}
    key = _user_key(user_id, chat_id)
    try:
        client.lpush(key, json.dumps(chat_entry))
        client.ltrim(key, 0, 9)  # keep only last 10 messages
    except Exception as e:
        print(f"⚠️ Failed to save chat to Redis: {e}")

def get_last_chats(user_id: int, chat_id: str | None = None, limit: int = 10):
    """
    Fetch last N chats from Redis (default 10)
    Returns list of dicts: [{"chat_id": ..., "user": ..., "bot": ...}, ...]
    """
    client = get_redis_client()
    if not client:
        return []

    key = _user_key(user_id, chat_id)
    try:
        chats = client.lrange(key, 0, limit - 1)
        return [json.loads(c) for c in chats]
    except Exception as e:
        print(f"⚠️ Failed to fetch chat from Redis: {e}")
        return []
