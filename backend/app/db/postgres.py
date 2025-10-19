import psycopg2
from psycopg2.extras import RealDictCursor  # ✅ fetch as dict
from app.config import settings

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
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
            user_query TEXT NOT NULL,
            ai_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Tables created or verified: tasks, chat_history")

# ---------------- TASK FUNCTIONS ----------------
def save_task(task_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (title, datetime, priority, category, notes, notified)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (
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

def get_tasks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY datetime;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ---------------- CHAT FUNCTIONS ----------------
def save_chat(user_query: str, ai_response: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO chat_history (user_query, ai_response)
        VALUES (%s, %s);
    """, (user_query, ai_response))
    conn.commit()
    cur.close()
    conn.close()
    print(f"💬 Chat saved: {user_query[:40]}...")

def get_chat_history(limit: int = 10):
    """
    Fetch last N chats from PostgreSQL chat_history table.
    Returns list of dicts: [{"user_query": ..., "ai_response": ...}, ...]
    ✅ Keeps the limit intact
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_query, ai_response FROM chat_history ORDER BY created_at DESC LIMIT %s;",
            (limit,)
        )
        rows = cur.fetchall()
        return rows
    finally:
        cur.close()
        conn.close()
