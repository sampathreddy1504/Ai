# backend/app/worker.py

import os
from celery import Celery
from datetime import datetime
import psycopg2
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# ======================
# 🔹 PostgreSQL Settings
# ======================
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "personal_ai")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# ======================
# 🔹 Redis (Celery Broker)
# ======================
REDIS_URL_CELERY = os.getenv("REDIS_URL_CELERY", "redis://redis:6379/0")

# ======================
# 🔹 Email Config
# ======================
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# ======================
# 🔹 Timezone
# ======================
INDIA_TZ = pytz.timezone("Asia/Kolkata")

# ======================
# 🔹 Celery Initialization
# ======================
celery = Celery(
    "worker",
    broker=REDIS_URL_CELERY,
    backend=REDIS_URL_CELERY
)

# Run check every minute
celery.conf.beat_schedule = {
    "check-tasks-every-1-minute": {
        "task": "worker.check_and_trigger_tasks",
        "schedule": 60.0,  # every 60 seconds
    },
}
celery.conf.timezone = "Asia/Kolkata"


# ======================
# 🔹 Main Task Checker
# ======================
@celery.task(name="worker.check_and_trigger_tasks")
def check_and_trigger_tasks():
    """
    Periodically checks PostgreSQL 'tasks' table for due reminders.
    Sends an email if a task is due (in IST timezone) and not yet notified.
    """
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port="5432"
        )
        cur = conn.cursor()

        # Force the DB session to IST timezone
        cur.execute("SET TIME ZONE 'Asia/Kolkata';")

        # Get all tasks that are due and not yet notified, including owner user_id
        cur.execute("""
            SELECT id, user_id, title, notes, datetime
            FROM tasks
            WHERE datetime <= NOW()
            AND (notified IS NULL OR notified = FALSE);
        """)
        tasks = cur.fetchall()

        triggered_count = 0

        for task_row in tasks:
            # task_row may be a tuple: (id, user_id, title, notes, datetime)
            try:
                task_id = task_row[0]
                task_user_id = task_row[1]
                title = task_row[2]
                desc = task_row[3]
            except Exception:
                # Fallback for different cursor types
                task_id = task_row.get("id")
                task_user_id = task_row.get("user_id")
                title = task_row.get("title")
                desc = task_row.get("notes")

            # Look up user's email and name from users table
            user_email = None
            user_name = None
            try:
                cur.execute("SELECT email, name FROM users WHERE id = %s;", (task_user_id,))
                user = cur.fetchone()
                if user:
                    # handle both tuple and dict cursor types
                    user_email = user[0] if isinstance(user, tuple) else user.get("email")
                    user_name = user[1] if isinstance(user, tuple) else user.get("name")
            except Exception as e:
                print(f"⚠️  Failed to lookup user {task_user_id}: {e}")

            # If user's email not available, skip sending and log
            if not user_email:
                print(f"⚠️  No email found for user {task_user_id}; skipping notification for task {task_id}")
            else:
                # Personalize message with user's name when available
                subject = f"Task Reminder: {title}"
                body = f"📌 Hi {user_name or 'there'},\n\nThis is a reminder for your task:\n\nTitle: {title}\nDetails: {desc or 'No details provided.'}\n\n— Your Personal AI Assistant"
                send_email_notification(user_email, subject, body)
                triggered_count += 1

                # Mark the task as notified
                cur.execute("UPDATE tasks SET notified = TRUE WHERE id = %s", (task_id,))
                conn.commit()

        cur.close()
        conn.close()

        now_ist = datetime.now(INDIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        print(f"✅ Checked tasks at {now_ist}, triggered {triggered_count} reminder(s).")

    except Exception as e:
        print("❌ Error checking tasks:", e)


# ======================
# 🔹 Email Notification
# ======================
def send_email_notification(to_email, title, desc):
    """
    Sends email notification using Gmail SMTP.
    """
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = EMAIL_USER
        sender_password = EMAIL_PASS

        msg = MIMEText(f"📌 Task Reminder\n\nTitle: {title}\n\nDetails: {desc or 'No details provided.'}")
        msg["Subject"] = f"Task Reminder: {title}"
        msg["From"] = sender_email
        msg["To"] = to_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [to_email], msg.as_string())

        print(f"📧 Email sent successfully to {to_email} for task '{title}'")

    except Exception as e:
        print("❌ Email send failed:", e)