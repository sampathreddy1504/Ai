import os
import psycopg2
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
from typing import Optional, Dict

# -------------------------------------------------
# DATABASE CONNECTION
# -------------------------------------------------
def get_connection():
    """
    Establish a PostgreSQL connection using DATABASE_URL if available (Render),
    or fallback to .env-based local settings.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        from app.config import settings
        return psycopg2.connect(
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            cursor_factory=RealDictCursor
        )

# -------------------------------------------------
# TABLE SETUP
# -------------------------------------------------
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # === USERS TABLE ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # === TASKS TABLE ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            datetime TIMESTAMP,
            priority TEXT,
            category TEXT,
            notes TEXT,
            notified BOOLEAN DEFAULT FALSE
        );
    """)

    # === CHAT HISTORY TABLE ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            chat_id TEXT,
            user_query TEXT NOT NULL,
            ai_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # === CHATS TABLE ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # === PENDING TASKS TABLE ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Lightweight migrations (safe schema evolution)
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;")
    cur.execute("ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;")
    cur.execute("ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS chat_id TEXT;")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Tables created or verified: users, tasks, chat_history, chats, pending_tasks")

# -------------------------------------------------
# TASKS
# -------------------------------------------------
def save_task(task_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (user_id, title, datetime, priority, category, notes, notified)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """, (
        task_data.get("user_id"),
        task_data.get("title"),
        task_data.get("datetime"),
        task_data.get("priority"),
        task_data.get("category"),
        task_data.get("notes", ""),
        False
    ))
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Task saved: {task_data.get('title')}")

def get_tasks(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY datetime;", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def delete_task(user_id: int, task_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s;", (task_id, user_id))
    deleted_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if deleted_count > 0:
        print(f"✅ Deleted task {task_id} for user {user_id}")
        return True
    print(f"❌ Task {task_id} not found or not owned by {user_id}")
    return False

def delete_completed_tasks(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tasks WHERE user_id = %s AND notified = TRUE RETURNING id;", (user_id,))
        deleted = cur.fetchall()
        conn.commit()
        return len(deleted)
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed deleting completed tasks: {e}")
        return 0
    finally:
        cur.close()
        conn.close()

def set_task_notified(user_id: int, task_id: int, notified: bool):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE tasks SET notified = %s WHERE id = %s AND user_id = %s RETURNING id;", (notified, task_id, user_id))
        updated = cur.fetchone()
        conn.commit()
        return bool(updated)
    except Exception as e:
        conn.rollback()
        print(f"❌ Update failed: {e}")
        return False
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------
# CHAT SYSTEM
# -------------------------------------------------
def save_chat(user_id: int, user_query: str, ai_response: str, chat_id: Optional[str] = None):
    conn = get_connection()
    cur = conn.cursor()
    import uuid

    # Ensure valid chat_id
    chat_id = chat_id or str(uuid.uuid4())

    # Create chat row if not exists
    cur.execute("SELECT 1 FROM chats WHERE id = %s;", (chat_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO chats (id, user_id) VALUES (%s, %s);", (chat_id, user_id))

    # Save message
    cur.execute("""
        INSERT INTO chat_history (user_id, chat_id, user_query, ai_response)
        VALUES (%s, %s, %s, %s);
    """, (user_id, chat_id, user_query, ai_response))

    # Update last_activity
    cur.execute("UPDATE chats SET last_activity = CURRENT_TIMESTAMP WHERE id = %s;", (chat_id,))
    conn.commit()
    cur.close()
    conn.close()
    print(f"💬 Chat saved for user {user_id}, chat_id={chat_id}")
    return chat_id

def get_chat_history(user_id: int, limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT chat_id, user_query, ai_response 
        FROM chat_history
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
    """, (user_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_conversations(user_id: int, limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT chat_id,
               MIN(created_at) AS first_at,
               MAX(created_at) AS last_at,
               (SELECT ch2.user_query FROM chat_history ch2 
                WHERE ch2.user_id = %s AND ch2.chat_id = ch.chat_id 
                ORDER BY ch2.created_at ASC LIMIT 1) AS first_msg
        FROM chat_history ch
        WHERE user_id = %s AND chat_id IS NOT NULL
        GROUP BY chat_id
        ORDER BY last_at DESC
        LIMIT %s;
    """, (user_id, user_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{
        "chat_id": r["chat_id"],
        "title": r["first_msg"] or "New chat",
        "last_at": r["last_at"].isoformat() if r["last_at"] else None
    } for r in rows]

def get_messages_by_chat(user_id: int, chat_id: str, limit: int = 200):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_query, ai_response
        FROM chat_history
        WHERE user_id = %s AND chat_id = %s
        ORDER BY created_at ASC
        LIMIT %s;
    """, (user_id, chat_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    messages = []
    for r in rows:
        messages.append({"type": "text", "sender": "user", "content": r["user_query"]})
        if r["ai_response"]:
            messages.append({"type": "text", "sender": "ai", "content": r["ai_response"]})
    return messages

# -------------------------------------------------
# PENDING TASKS
# -------------------------------------------------
def save_pending_task(user_id: int, title: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO pending_tasks (user_id, title) VALUES (%s, %s);", (user_id, title))
    conn.commit()
    cur.close()
    conn.close()

def get_pending_task(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM pending_tasks WHERE user_id = %s ORDER BY created_at DESC LIMIT 1;", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def delete_pending_task(pending_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_tasks WHERE id = %s;", (pending_id,))
    conn.commit()
    cur.close()
    conn.close()

# -------------------------------------------------
# AUTH HELPERS
# -------------------------------------------------
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password.strip())

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_user(name: str, email: str, password: str) -> Dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (name, email, password_hash)
        VALUES (%s, %s, %s)
        RETURNING id, name, email;
    """, (name, email, hash_password(password)))
    user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return user

def get_user_by_email(email: str) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s;", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users WHERE id = %s;", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def update_user_profile(user_id: int, name: Optional[str] = None, email: Optional[str] = None):
    if not name and not email:
        return False
    conn = get_connection()
    cur = conn.cursor()
    try:
        if name and email:
            cur.execute("UPDATE users SET name = %s, email = %s WHERE id = %s;", (name, email, user_id))
        elif name:
            cur.execute("UPDATE users SET name = %s WHERE id = %s;", (name, user_id))
        elif email:
            cur.execute("UPDATE users SET email = %s WHERE id = %s;", (email, user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to update profile: {e}")
        return False
    finally:
        cur.close()
        conn.close()
