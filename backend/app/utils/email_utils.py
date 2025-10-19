import os
import smtplib
from email.mime.text import MIMEText

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


def send_welcome_email(to_email: str, name: str | None = None):
    if not EMAIL_USER or not EMAIL_PASS or not to_email:
        return False
    try:
        subject = "Welcome to Your Personal AI Assistant"
        body = f"Hi {name or ''},\n\nWelcome! We're glad you signed up. Start chatting with your personal assistant anytime.\n\n— Your Personal AI Assistant"
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [to_email], msg.as_string())
        return True
    except Exception:
        return False
