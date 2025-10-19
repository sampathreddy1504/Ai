# redis_utils.py
from app.config import settings
import redis, json

# Use Redis DB for chat history explicitly
client = redis.Redis.from_url(settings.REDIS_URL_CHAT, decode_responses=True)

def get_redis_client():
    return client

def _user_key(user_id: int) -> str:
    return f"{settings.REDIS_CHAT_HISTORY_KEY}:{user_id}"

def save_chat_redis(user_id: int, user_message: str, bot_reply: str, chat_id: str | None = None):
    chat_entry = {"chat_id": chat_id, "user": user_message, "bot": bot_reply}
    key = _user_key(user_id)
    client.lpush(key, json.dumps(chat_entry))
    client.ltrim(key, 0, 9)  # keep only last 10 messages

def get_last_chats(user_id: int, limit: int = 10):
    """
    Fetch last N chats from Redis (default 10)
    Returns list of dicts: [{"user": ..., "bot": ...}, ...]
    """
    key = _user_key(user_id)
    chats = client.lrange(key, 0, limit-1)
    return [json.loads(c) for c in chats]
