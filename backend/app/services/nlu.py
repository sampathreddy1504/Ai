import re
from datetime import datetime, timedelta
import pytz

# Use India Standard Time (IST)
IST = pytz.timezone("Asia/Kolkata")


def parse_time_string(time_str: str):
    """
    Converts a time string like '8am', '7:30 PM', '10:00pm', '7 PM',
    '8:25pm today', '8pm tomorrow', 'in 2 hours', 'in 30 minutes'
    into a full IST datetime string: YYYY-MM-DD HH:MM:SS
    """
    if not time_str:
        return None

    time_str = time_str.strip().replace(".", "").lower()

    # Detect 'today' or 'tomorrow'
    day_offset = 0
    if "tomorrow" in time_str:
        day_offset = 1
        time_str = time_str.replace("tomorrow", "").strip()
    elif "today" in time_str:
        time_str = time_str.replace("today", "").strip()

    # Normalize AM/PM spacing
    if time_str.endswith("am") or time_str.endswith("pm"):
        if not re.search(r"\s(am|pm)$", time_str):
            time_str = time_str[:-2] + " " + time_str[-2:]

    # Try parsing multiple formats
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            today_ist = datetime.now(IST).date()
            final_date = today_ist + timedelta(days=day_offset)
            local_dt = datetime.combine(final_date, parsed_time.time())
            ist_dt = IST.localize(local_dt)
            return ist_dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    # Handle relative times like 'in 2 hours' or 'in 30 minutes'
    m = re.search(r'in\s+(\d+)\s+(minute|minutes|hour|hours)', time_str)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        now_local = datetime.now(IST)
        if 'hour' in unit:
            final_dt = now_local + timedelta(hours=amount)
        else:
            final_dt = now_local + timedelta(minutes=amount)
        return final_dt.strftime("%Y-%m-%d %H:%M:%S")

    return None


def get_structured_intent(user_message: str) -> dict:
    """
    Parse the user message into a structured intent dictionary.
    Supports:
    - save facts
    - create tasks / reminders
    - fetch tasks
    - get chat history
    - open external apps (youtube, maps, whatsapp, spotify, instagram)
    - general chat
    """
    msg = user_message.lower().strip()
    msg = re.sub(r'^(please\s+|please,\s+|can you\s+|could you\s+|would you\s+)', '', msg)

    # ---------- Save Fact ----------
    match_fact = re.match(r"(save|remember) fact (.+?) as (.+)", msg)
    if match_fact:
        key = match_fact.group(2).strip()
        value = match_fact.group(3).strip()
        return {"action": "save_fact", "data": {"key": key, "value": value}}

    match_generic_fact = re.match(r"(remember|my) (.+?) is (.+)", msg)
    if match_generic_fact:
        key = match_generic_fact.group(2).strip()
        value = match_generic_fact.group(3).strip()
        return {"action": "save_fact", "data": {"key": key, "value": value}}

    # ---------- Task / Reminder ----------
    # "create task ... due ..."
    match_task = re.match(r"(?:create|add) task (.+?) due (.+)", msg)
    if match_task:
        title = match_task.group(1).strip()
        datetime_value = parse_time_string(match_task.group(2).strip())
        return {
            "action": "create_task",
            "data": {"title": title, "datetime": datetime_value, "priority": "medium", "category": "personal", "notes": ""}
        }

    # "remind me to ..."
    match_reminder = re.match(r"remind me to (.+?)(?: at (.+))?$", msg)
    if match_reminder:
        title = match_reminder.group(1).strip()
        time_part = match_reminder.group(2).strip() if match_reminder.group(2) else None
        if not time_part:
            tsrch = re.search(r"((?:\d{1,2}(?::\d{2})?\s?(?:am|pm))|\b(?:today|tomorrow)\b|in\s+\d+\s+(?:minute|minutes|hour|hours))", title)
            if tsrch:
                time_part = tsrch.group(1)
                title = title.replace(time_part, "").strip()
        datetime_value = parse_time_string(time_part) if time_part else None
        return {
            "action": "create_task",
            "data": {"title": title, "datetime": datetime_value, "priority": "medium", "category": "personal", "notes": ""}
        }

    # Flexible add/create task patterns
    match_task_flex = re.match(r"(?:add|create)(?: me)?(?: a)?(?: task| reminder)?(?: to)? (.+?)(?: at (.+))?$", msg)
    if match_task_flex:
        title = match_task_flex.group(1).strip()
        time_part = match_task_flex.group(2).strip() if match_task_flex.group(2) else None
        if not time_part:
            tsrch = re.search(r"((?:\d{1,2}(?::\d{2})?\s?(?:am|pm))|\b(?:today|tomorrow)\b|in\s+\d+\s+(?:minute|minutes|hour|hours))", title)
            if tsrch:
                time_part = tsrch.group(1)
                title = title.replace(time_part, "").strip()
        datetime_value = parse_time_string(time_part) if time_part else None
        return {"action": "create_task", "data": {"title": title, "datetime": datetime_value, "priority": "medium", "category": "personal", "notes": ""}}

    # ---------- Fetch Tasks ----------
    if any(k in msg for k in ["show tasks", "list tasks", "my tasks"]):
        return {"action": "fetch_tasks"}

    # ---------- Get Last Chat History ----------
    if any(k in msg for k in ["show chat history", "last chats", "previous messages"]):
        return {"action": "get_chat_history"}

    # ---------- External Apps ----------
    external_apps = ["youtube", "maps", "whatsapp", "spotify", "instagram"]
    for app in external_apps:
        if app in msg:
            query = ""
            # Look for patterns like 'play X on youtube', 'search maps for Y', etc.
            m = re.match(rf"(?:play|search|find|open|launch|go to) (.+?) on {app}\b", msg) or \
                re.match(rf"{app}[:\-\s]+(.+)", msg)
            if m:
                query = m.group(1).strip()
            return {"action": "open_external", "data": {"target": app, "query": query}}

    # ---------- Greeting / identity / default ----------
    return {"action": "general_chat"}
