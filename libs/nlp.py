# libs/nlp.py
import re
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
    "high": ["urgent", "asap", "immediately", "deadline", "emergency"],
    "medium": ["soon", "next week", "priority"],
    "low": ["whenever", "no rush", "just checking", "informational"]
}

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

def detect_urgency(text: str):
    t = (text or "").lower()
    for level, keywords in URGENCY_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return level
    return "low"

def is_automated_reply(text: str):
    return bool(re.search(r"\b(auto|automated|no-reply|noreply|out of office|vacation)\b", (text or "").lower()))
