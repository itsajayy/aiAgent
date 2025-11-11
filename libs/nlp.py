# libs/nlp.py
import re
from datetime import datetime, timedelta
import pandas as pd
from dateutil.parser import parse

TOPIC_KEYWORDS = {
    "course registration": ["register", "registration", "enroll", "course add", "add course"],
    "academic advising": ["advisor", "advice", "advising", "counsel"],
    "graduation requirements": ["graduate", "graduation", "degree audit", "requirements", "degree"],
    "meeting scheduled": ["meeting", "schedule", "booked", "appointment"],
    "holds in general": ["hold", "restriction", "finance hold", "registration block"],
}

URGENCY_KEYWORDS = {
    "high": [
        "urgent",
        "asap",
        "immediately",
        "right away",
        "eod",
        "end of day",
        "cob",
        "close of business",
        "today",
        "tonight",
        "emergency",
        "time-sensitive",
        "critical",
        "due today",
        "tomorrow",
        "by tomorrow",
        "deadline",
    ],
    "medium": [
        "soon",
        "this week",
        "next week",
        "priority",
        "whenever possible",
    ],
    "low": [
        "whenever",
        "no rush",
        "just checking",
        "informational",
        "fyi",
    ],
}

# Weekday names for lightweight date inference
WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

def detect_sender_type(email_address: str):
    if not isinstance(email_address, str): return "other"
    email_address = email_address.lower()
    if email_address.endswith("@umd.edu") or "terp" in email_address:
        return "student"
    if email_address.endswith(".edu"):
        return "faculty/staff"
    return "other"

def classify_topic(text: str):
    text_l = (text or "").lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_l:
                return topic
    return "other"

def _extract_candidate_deadlines(t: str):
    """Yield parsed datetimes for common deadline phrases.

    Looks for patterns like:
      - by/before/due/deadline <phrase>
      - on <weekday/date>
      - explicit weekdays (e.g., Friday) or relative words (tomorrow)
    """
    now = datetime.now()
    candidates = []

    # Relative words
    if re.search(r"\b(tomorrow|tmrw)\b", t):
        candidates.append(now + timedelta(days=1))
    if re.search(r"\b(today|tonight|eod|end of day|cob|close of business)\b", t):
        # Assume by end of today if mentioned
        candidates.append(datetime(now.year, now.month, now.day, 17, 0))

    # Weekdays mentioned alone (e.g., "by Friday")
    for wd in WEEKDAYS:
        if re.search(rf"\b{wd}\b", t):
            # parse picks the next occurrence given default=now
            try:
                candidates.append(parse(wd, fuzzy=True, default=now))
            except Exception:
                pass

    # Phrases like: by/before/due/deadline/on <something>
    for m in re.finditer(r"\b(?:by|before|due(?:\s+on)?|deadline(?:\s+is)?|on)\s+([^\n\r;,.]+)", t):
        phrase = m.group(1).strip()
        # Trim trailing courtesy words
        phrase = re.sub(r"\b(please|thanks|thank you)\b.*$", "", phrase).strip()
        try:
            dt = parse(phrase, fuzzy=True, default=now)
            # If only a time was given and it's already passed today, bump to next day
            if dt <= now and re.search(r"\b\d{1,2}(:\d\d)?\s*(am|pm)\b", phrase):
                dt = dt + timedelta(days=1)
            candidates.append(dt)
        except Exception:
            continue

    # Return soonest unique candidates
    uniq = sorted({c for c in candidates if isinstance(c, datetime)})
    return uniq


def detect_urgency(text: str):
    t = (text or "").lower()

    # 1) Direct keyword hits take precedence
    for kw in URGENCY_KEYWORDS["high"]:
        if kw in t:
            return "high"
    for kw in URGENCY_KEYWORDS["medium"]:
        if kw in t:
            return "medium"
    for kw in URGENCY_KEYWORDS["low"]:
        if kw in t:
            return "low"

    # 2) Punctuation/emphasis heuristics
    if t.count("!") >= 2:
        return "high"

    # 3) Deadline/date inference
    candidates = _extract_candidate_deadlines(t)
    if candidates:
        now = datetime.now()
        soonest = min(candidates)
        delta = soonest - now
        if delta <= timedelta(days=2):
            return "high"
        if delta <= timedelta(days=7):
            return "medium"

    # 4) Default fallback
    return "low"

def is_automated_reply(text: str):
    return bool(re.search(r"\b(auto|automated|no-reply|noreply|out of office|vacation)\b", (text or "").lower()))
