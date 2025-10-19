# backend/app/services/memory.py
import json
from app.db import redis_utils as redis, postgres as postgres
from app.db.neo4j_utils import (
    save_fact_neo4j,
    get_fact_neo4j,
    get_all_facts_for_user,
)

# =========================================================
# 🔹 USER FACTS (Neo4j)
# =========================================================
def save_user_fact(user_id: str, key: str, value: str):
    """
    Persist a long-term user fact (e.g., name, preferences).
    """
    save_fact_neo4j(user_id, key, value)


def get_user_fact(user_id: str, key: str):
    """
    Retrieve one user fact.
    """
    return get_fact_neo4j(user_id, key)


def get_all_user_facts(user_id: str) -> dict:
    """
    Retrieve all stored user facts as a dictionary.
    """
    try:
        facts = get_all_facts_for_user(user_id)
        if isinstance(facts, str):
            try:
                return json.loads(facts)
            except json.JSONDecodeError:
                return {"fact": facts}
        return facts or {}
    except Exception as e:
        return {"error": str(e)}


# =========================================================
# 🔹 TASKS (PostgreSQL)
# =========================================================
def save_task(task_data: dict):
    postgres.save_task(task_data)


def get_tasks():
    return postgres.get_tasks()


# =========================================================
# 🔹 CHAT HISTORY (Redis)
# =========================================================
def save_chat_history(user_id: str, user_message: str, bot_reply: str):
    """
    Save last 10 messages per user in Redis.
    """
    redis.save_chat(user_id, user_message, bot_reply)


def get_last_chats(user_id: str):
    return redis.get_last_chats(user_id)
