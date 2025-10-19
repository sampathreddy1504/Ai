Quick fix: Real-time date/time handler

What changed
- Added a small, local handler in `app/services/ai_services.py` inside `get_response`.
- When the user's message clearly asks for the current date or time (common phrasings), the backend returns the server's local date/time immediately instead of sending the question to the LLM. This prevents placeholder text like "[current date]" from being returned.

Why
- LLMs may include placeholders or hallucinate current-time information. For simple facts like current date/time, it's safer and faster to answer locally.

Timezone
- The handler uses Python's `datetime.now()` which returns the server's local time. If you want the assistant to use a specific timezone (e.g., the user's timezone), update the handler to use `pytz` or `zoneinfo` and a configured timezone setting.

How to extend
- Add more phrase matches if you're seeing other variants.
- For multi-lingual support, add phrase lists per language or do quick intent detection and then format accordingly.

Notes
- This is a lightweight, non-invasive fix that shouldn't affect other AI features. If you run into missing-dependency errors when importing the full app (e.g., `pydantic_settings`, `cohere`), install project dependencies listed in `requirements.txt` before running the backend.
