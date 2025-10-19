import re
from datetime import datetime, date, timedelta
import pytz

# Use India Standard Time (IST)
IST = pytz.timezone("Asia/Kolkata")


def parse_time_string(time_str: str):
    """
    Converts a time string like '8am', '7:30 PM', '10:00pm', '7 PM',
    '8:25pm today', or '8pm tomorrow' into a full IST datetime string: YYYY-MM-DD HH:MM:SS
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

    # Try to parse using multiple time formats
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            # Use IST-aware current date so 'today'/'tomorrow' are computed in user's timezone
            today_ist = datetime.now(IST).date()
            final_date = today_ist + timedelta(days=day_offset)
            local_dt = datetime.combine(final_date, parsed_time.time())
            # Attach IST timezone
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
    - open external: youtube/maps/whatsapp
    - general chat
    """
    # Normalize and strip polite prefixes to simplify pattern matching
    msg = user_message.lower().strip()
    msg = re.sub(r'^(please\s+|please,\s+|can you\s+|could you\s+|would you\s+)', '', msg)

    # ---------- Save Fact (explicit) ----------
    match_fact = re.match(r"(save|remember) fact (.+?) as (.+)", msg)
    if match_fact:
        key = match_fact.group(2).strip()
        value = match_fact.group(3).strip()
        return {"action": "save_fact", "data": {"key": key, "value": value}}

    # ---------- Save Fact (generic) ----------
    match_generic_fact = re.match(r"(remember|my) (.+?) is (.+)", msg)
    if match_generic_fact:
        key = match_generic_fact.group(2).strip()
        value = match_generic_fact.group(3).strip()
        return {"action": "save_fact", "data": {"key": key, "value": value}}

    # ---------- Create / Reminder Task (more flexible) ----------
    # Patterns supported:
    # - "create task <title> due <time>"
    # - "add task to <title> at <time>"
    # - "add a task to <title>" (optional time)
    # - "remind me to <title> at <time>"
    # - Polite prefixes like 'can you', 'please' are stripped above

    # Try exact "create task ... due ..."
    match_task = re.match(r"(?:create|add) task (.+?) due (.+)", msg)
    if match_task:
        title = match_task.group(1).strip()
        time_part = match_task.group(2).strip()
        datetime_value = parse_time_string(time_part) or None
        return {
            "action": "create_task",
            "data": {
                "title": title,
                "datetime": datetime_value,
                "priority": "medium",
                "category": "personal",
                "notes": "",
            },
        }

    # "remind me to <action> at <time>" (common natural phrasing)
    match_reminder = re.match(r"remind me to (.+?)(?: at (.+))?$,", msg)
    # The previous regex above had a trailing comma; handle with a safer pattern below
    match_reminder = re.match(r"remind me to (.+?)(?: at (.+))?$", msg)
    if match_reminder:
        title = match_reminder.group(1).strip()
        time_part = match_reminder.group(2).strip() if match_reminder.group(2) else None
        # If time_part is not provided, try to find time tokens inside the title
        if not time_part:
            tsrch = re.search(r"((?:\d{1,2}(?::\d{2})?\s?(?:am|pm))|\b(?:today|tomorrow)\b|in\s+\d+\s+(?:minute|minutes|hour|hours))", title)
            if tsrch:
                time_part = tsrch.group(1)
                title = title.replace(time_part, "").strip()
        datetime_value = parse_time_string(time_part) if time_part else None
        return {
            "action": "create_task",
            "data": {
                "title": title,
                "datetime": datetime_value,
                "priority": "medium",
                "category": "personal",
                "notes": "",
            },
        }

    # Flexible "add/create (a) task to <title> [at <time>]" or "add me a task to <title>"
    match_task_flex = re.match(r"(?:add|create)(?: me)?(?: a)?(?: task| reminder)?(?: to)? (.+?)(?: at (.+))?$", msg)
    if match_task_flex:
        title = match_task_flex.group(1).strip()
        time_part = match_task_flex.group(2).strip() if match_task_flex.group(2) else None
        # If time not captured, search anywhere in the title
        if not time_part:
            tsrch = re.search(r"((?:\d{1,2}(?::\d{2})?\s?(?:am|pm))|\b(?:today|tomorrow)\b|in\s+\d+\s+(?:minute|minutes|hour|hours))", title)
            if tsrch:
                time_part = tsrch.group(1)
                title = title.replace(time_part, "").strip()
        datetime_value = parse_time_string(time_part) if time_part else None
        return {
            "action": "create_task",
            "data": {
                "title": title,
                "datetime": datetime_value,
                "priority": "medium",
                "category": "personal",
                "notes": "",
            },
        }

    # ---------- Fetch Tasks ----------
    if any(keyword in msg for keyword in ["show tasks", "list tasks", "my tasks"]):
        return {"action": "fetch_tasks"}

    # ---------- Get Last Chat History ----------
    if any(
        keyword in msg for keyword in ["show chat history", "last chats", "previous messages"]
    ):
        return {"action": "get_chat_history"}

    # ---------- External: YouTube ----------
    # Support forms: 'play X on youtube', 'open youtube and search for X', 'search youtube for X', 'youtube: X', and action-only 'open youtube'
    if not any(k in msg for k in ["what is youtube", "tell me about youtube", "about youtube"]):
        m = None
        # "play X on youtube" or "find X on youtube"
        m = re.match(r"(?:search|find|play) (.+) on (?:youtube)\b", msg)
        # "open youtube and search for X" or "open youtube search X"
        if not m:
            m = re.match(r"(?:open) (?:youtube) (?:and )?(?:search(?: for)?)? (.+)", msg)
        # "search youtube for X" or "youtube: X"
        if not m:
            m = re.match(r"(?:search|find) (?:youtube) (?:for )?(.+)", msg)
        if not m:
            m = re.match(r"(?:youtube[:\-\s]+)(.+)", msg)
        # action-only: 'open youtube' or 'launch youtube'
        if not m:
            m = re.match(r"^(?:open|launch|go to) (?:youtube)\b", msg)
            if m:
                return {"action": "open_external", "data": {"target": "youtube", "query": ""}}
        if m:
            query = m.group(1).strip()
            return {"action": "open_external", "data": {"target": "youtube", "query": query}}

    # ---------- External: Google Maps ----------
    # Maps: support 'open maps for X', 'navigate to X', 'find X on maps', 'navigate me to', 'take me to', and action-only 'open maps'
    if not any(k in msg for k in ["what is maps", "tell me about maps", "about maps"]):
        m = None
        m = re.match(r"(?:open|search) (?:maps|google maps) (?:for )?(.+)", msg)
        if not m:
            m = re.match(r"(?:find|navigate to|navigate me to|take me to|go to) (.+)", msg)
        if not m:
            m = re.match(r"maps[:\-\s]+(.+)", msg)
        # action-only 'open maps'
        if not m:
            m = re.match(r"^(?:open|launch|go to) (?:maps|google maps)\b", msg)
            if m:
                return {"action": "open_external", "data": {"target": "maps", "query": ""}}
        if m:
            query = m.group(1).strip()
            return {"action": "open_external", "data": {"target": "maps", "query": query}}

    # ---------- External: WhatsApp ----------
    wa = re.match(r"(?:open|send on )?whatsapp(?: to)? (.+)", msg) or re.match(r"whatsapp[:\-\s]+(.+)", msg)
    if wa:
        query = wa.group(1).strip()
        return {"action": "open_external", "data": {"target": "whatsapp", "query": query}}

    # ---------- External: Spotify ----------
    # Spotify: 'play <song> on spotify', 'open spotify and search for <query>', 'spotify: <query>' and action-only 'open spotify'
    if not any(k in msg for k in ["what is spotify", "tell me about spotify", "about spotify"]):
        m = None
        m = re.match(r"(?:play|find) (.+) on (?:spotify)\b", msg)
        if not m:
            m = re.match(r"(?:open) (?:spotify) (?:and )?(?:search(?: for)?)? (.+)", msg)
        if not m:
            m = re.match(r"spotify[:\-\s]+(.+)", msg)
        # action-only 'open spotify'
        if not m:
            m = re.match(r"^(?:open|launch|go to) (?:spotify)\b", msg)
            if m:
                return {"action": "open_external", "data": {"target": "spotify", "query": ""}}
        if m:
            query = m.group(1).strip()
            return {"action": "open_external", "data": {"target": "spotify", "query": query}}

    # ---------- External: Instagram ----------
    # Instagram: 'open instagram and search for X', 'instagram: X' and action-only 'open instagram'
    if not any(k in msg for k in ["what is instagram", "tell me about instagram", "about instagram"]):
        m = None
        m = re.match(r"(?:open|search|show|find) (?:instagram) (?:and )?(?:search(?: for)?)? (.+)", msg)
        if not m:
            m = re.match(r"instagram[:\-\s]+(.+)", msg)
        # action-only 'open instagram'
        if not m:
            m = re.match(r"^(?:open|launch|go to) (?:instagram)\b", msg)
            if m:
                return {"action": "open_external", "data": {"target": "instagram", "query": ""}}
        if m:
            query = m.group(1).strip()
            return {"action": "open_external", "data": {"target": "instagram", "query": query}}

    # ---------- General Chat ----------
    return {"action": "general_chat"}