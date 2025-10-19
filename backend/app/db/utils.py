import psycopg2
from psycopg2.extras import RealDictCursor  # ✅ Added to get dicts instead of tuples
from app.config import settings
from passlib.context import CryptContext
from typing import Optional, Dict


# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    return psycopg2.connect(
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        cursor_factory=RealDictCursor  # ✅ ensures fetch returns dicts
    )


# ---------------- TABLE SETUP ----------------
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # Users table for authentication
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

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

    # Chats table: canonical conversation identifier (server-generated UUID)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Lightweight migrations for existing databases
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;")
    cur.execute("ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;")
    cur.execute("ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS chat_id TEXT;")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Tables created or verified: tasks, chat_history")


# ---------------- TASK FUNCTIONS ----------------
def save_task(task_data: dict):
    conn = get_connection()
    cur = conn.cursor()

    # ✅ Fixed VALUES to match all 6 columns (notified added)
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
    """Delete a task for a specific user"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Delete task only if it belongs to the user
    cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s;", (task_id, user_id))
    deleted_count = cur.rowcount
    
    conn.commit()
    cur.close()
    conn.close()
    
    if deleted_count > 0:
        print(f"✅ Task {task_id} deleted for user {user_id}")
        return True
    else:
        print(f"❌ Task {task_id} not found or doesn't belong to user {user_id}")
        return False


def delete_completed_tasks(user_id: int):
    """Delete all tasks marked as completed (notified = TRUE) for the user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tasks WHERE user_id = %s AND notified = TRUE RETURNING id;", (user_id,))
        deleted = cur.fetchall()
        conn.commit()
        deleted_count = len(deleted) if deleted else 0
        print(f"✅ Deleted {deleted_count} completed tasks for user {user_id}")
        return deleted_count
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to delete completed tasks for user {user_id}: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


def set_task_notified(user_id: int, task_id: int, notified: bool):
    """Set the notified flag for a specific task belonging to a user."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE tasks SET notified = %s WHERE id = %s AND user_id = %s RETURNING id;", (notified, task_id, user_id))
        updated = cur.fetchone()
        conn.commit()
        return bool(updated)
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to update task {task_id} for user {user_id}: {e}")
        return False
    finally:
        cur.close()
        conn.close()


# ---------------- CHAT FUNCTIONS ----------------
def save_chat(user_id: int, user_query: str, ai_response: str, chat_id: Optional[str] = None):
    conn = get_connection()
    cur = conn.cursor()

    print(f"💾 Saving chat - user_id: {user_id}, chat_id: {chat_id}, query: {user_query[:40]}...")

    # Ensure the referenced user exists to avoid foreign key violations.
    try:
        cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
        user_row = cur.fetchone()
    except Exception:
        # In case the users table doesn't exist (older schema), user_row will be None
        user_row = None

    if not user_row:
        print(f"⚠️  User {user_id} not found in 'users' table. Creating placeholder user.")
        try:
            # Try to insert a placeholder user with the requested id. This handles cases where
            # tokens contain an externally-assigned numeric id.
            cur.execute(
                "INSERT INTO users (id, name, email, password_hash) VALUES (%s, %s, %s, %s);",
                (user_id, f"placeholder_{user_id}", f"placeholder+{user_id}@example.local", hash_password("changeme"))
            )
            # Ensure the serial sequence for users.id is at least the current max id
            cur.execute("SELECT setval(pg_get_serial_sequence('users','id'), (SELECT MAX(id) FROM users));")
            conn.commit()
            print(f"✅ Placeholder user {user_id} created.")
        except Exception as e:
            # If inserting with explicit id fails (e.g. sequence/permission), rollback and try
            # creating a user without specifying id and then use that id for the chat.
            print(f"⚠️  Failed to insert placeholder user with id {user_id}: {e}. Trying fallback insert.")
            conn.rollback()
            try:
                cur.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id;",
                    (f"placeholder_{user_id}", f"placeholder+{user_id}@example.local", hash_password("changeme"))
                )
                new_user = cur.fetchone()
                if new_user:
                    # RealDictCursor returns a dict
                    new_id = new_user.get("id") if isinstance(new_user, dict) else new_user[0]
                    print(f"✅ Fallback user created with id {new_id}; will use this id for chat.")
                    user_id = new_id
                conn.commit()
            except Exception as e2:
                print(f"❌ Fallback insert also failed: {e2}. Proceeding to attempt chat insert which may fail.")
                conn.rollback()

    try:
        # If no chat_id provided, create a canonical chat row and use its id
        used_chat_id = chat_id
        if not used_chat_id:
            import uuid
            used_chat_id = str(uuid.uuid4())
            try:
                cur.execute("INSERT INTO chats (id, user_id) VALUES (%s, %s);", (used_chat_id, user_id))
            except Exception:
                # ignore failures creating chat row (best-effort)
                pass

        cur.execute("""
            INSERT INTO chat_history (user_id, chat_id, user_query, ai_response)
            VALUES (%s, %s, %s, %s);
        """, (user_id, used_chat_id, user_query, ai_response))

        # Update chats.last_activity if the chat exists
        try:
            cur.execute("UPDATE chats SET last_activity = CURRENT_TIMESTAMP WHERE id = %s;", (used_chat_id,))
        except Exception:
            pass

        conn.commit()
        print(f"💬 Chat saved: {user_query[:40]}... (chat_id={used_chat_id})")
        return used_chat_id
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to save chat for user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


# ✅ Corrected to return dicts compatible with main.py
def get_chat_history(user_id: int, limit: int = 10):
    """
    Fetch last N chats from PostgreSQL chat_history table.
    Returns list of dicts: [{"user_query": ..., "ai_response": ...}, ...]
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT chat_id, user_query, ai_response FROM chat_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s;",
            (user_id, limit)
        )
        rows = cur.fetchall()
        return rows
    finally:
        cur.close()
        conn.close()
def get_conversations(user_id: int, limit: int = 50):
    """
    Returns latest conversations grouped by chat_id with a title inferred from first user message.
    [{"chat_id": str, "title": str, "last_at": timestamp}]
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # First, get conversations with chat_id
    cur.execute(
        """
        SELECT chat_id,
               MIN(created_at) AS first_at,
               MAX(created_at) AS last_at,
               (SELECT ch2.user_query FROM chat_history ch2 WHERE ch2.user_id = %s AND ch2.chat_id = ch.chat_id ORDER BY ch2.created_at ASC LIMIT 1) AS first_msg
        FROM chat_history ch
        WHERE user_id = %s AND chat_id IS NOT NULL
        GROUP BY chat_id
        ORDER BY last_at DESC
        LIMIT %s;
        """,
        (user_id, user_id, limit)
    )
    rows_with_chat_id = cur.fetchall()
    
    # Also get individual messages without chat_id (for backward compatibility)
    cur.execute(
        """
        SELECT id as chat_id,
               created_at AS first_at,
               created_at AS last_at,
               user_query AS first_msg
        FROM chat_history
        WHERE user_id = %s AND chat_id IS NULL
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (user_id, limit)
    )
    rows_without_chat_id = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # Combine and map to desired structure
    results = []
    
    # Add conversations with chat_id
    for r in rows_with_chat_id:
        title = r.get("first_msg") or "New chat"
        results.append({
            "chat_id": r["chat_id"], 
            "title": title, 
            "last_at": r["last_at"].isoformat() if r["last_at"] else None
        })
    
    # Add individual messages without chat_id (convert id to string for chat_id)
    for r in rows_without_chat_id:
        title = r.get("first_msg") or "New chat"
        results.append({
            "chat_id": str(r["chat_id"]),  # Use database ID as chat_id
            "title": title, 
            "last_at": r["last_at"].isoformat() if r["last_at"] else None
        })
    
    # Sort by last_at and limit
    results.sort(key=lambda x: x["last_at"] or "", reverse=True)
    return results[:limit]


# ---------------- PENDING TASKS ----------------
def save_pending_task(user_id: int, title: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO pending_tasks (user_id, title) VALUES (%s, %s);",
        (user_id, title)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_pending_task(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title FROM pending_tasks WHERE user_id = %s ORDER BY created_at DESC LIMIT 1;",
        (user_id,)
    )
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


def get_messages_by_chat(user_id: int, chat_id: str, limit: int = 200):
    """Return ordered messages for a chat_id as list of dicts with role & content."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Try to get messages with the chat_id first
    cur.execute(
        """
        SELECT user_query, ai_response
        FROM chat_history
        WHERE user_id = %s AND chat_id = %s
        ORDER BY created_at ASC
        LIMIT %s;
        """,
        (user_id, chat_id, limit)
    )
    rows = cur.fetchall()
    
    # If no messages found with chat_id, check if it's a database ID (for backward compatibility)
    if not rows:
        try:
            db_id = int(chat_id)
            cur.execute(
                """
                SELECT user_query, ai_response
                FROM chat_history
                WHERE user_id = %s AND id = %s
                ORDER BY created_at ASC
                LIMIT %s;
                """,
                (user_id, db_id, limit)
            )
            rows = cur.fetchall()
        except ValueError:
            # chat_id is not a number, so it's a proper UUID chat_id with no messages
            pass
    
    cur.close()
    conn.close()
    messages = []
    for r in rows:
        messages.append({"type": "text", "sender": "user", "content": r["user_query"]})
        if r["ai_response"]:
            messages.append({"type": "text", "sender": "ai", "content": r["ai_response"]})
    return messages


# ---------------- AUTH HELPERS ----------------
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def hash_password(plain_password: str) -> str:
    # Ensure password length compatibility for bcrypt; argon2 supports long inputs
    if isinstance(plain_password, str):
        plain_password = plain_password.strip()
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_user(name: str, email: str, plain_password: str) -> Dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name, email;",
        (name, email, hash_password(plain_password))
    )
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
    """Return user dict for given id or None if not found."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, email FROM users WHERE id = %s;", (user_id,))
        user = cur.fetchone()
        return user
    finally:
        cur.close()
        conn.close()


def update_user_profile(user_id: int, name: str | None = None, email: str | None = None):
    """Update user's name and/or email if provided."""
    if not name and not email:
        return False
    conn = get_connection()
    cur = conn.cursor()
    try:
        import logging
        logger = logging.getLogger(__name__)
        if name and email:
            cur.execute("UPDATE users SET name = %s, email = %s WHERE id = %s;", (name, email, user_id))
        elif name:
            cur.execute("UPDATE users SET name = %s WHERE id = %s;", (name, user_id))
        elif email:
            cur.execute("UPDATE users SET email = %s WHERE id = %s;", (email, user_id))
        conn.commit()
        logger.info(f"Updated profile for user {user_id}: name={name}, email={email}")
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()
