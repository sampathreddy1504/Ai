from datetime import datetime

def quick_response(user_text: str) -> str:
    lt = user_text.lower().strip()
    date_phrases = [
        "what is the date",
        "what's the date",
        "date today",
        "what is today's date",
        "what's today's date",
        "what day is it",
        "what day is today",
        "day today",
        "today's date",
        "what is today",
        "what day is it today",
    ]
    time_phrases = [
        "what time is it",
        "what's the time",
        "current time",
        "time now",
    ]

    if any(p in lt for p in date_phrases):
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        return f"Today is {date_str}."

    if any(p in lt for p in time_phrases):
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        return f"The current time is {time_str}."

    return "no match"

if __name__ == '__main__':
    print(quick_response("What is the date today?"))
    print(quick_response("What's the time now?"))
    print(quick_response("Tell me about your features."))
