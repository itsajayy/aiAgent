# libs/llm_client.py
import os
import streamlit as st

try:
    from groq import Groq
except Exception as e:
    # Defer import error until used to keep app load resilient
    Groq = None


# Initialize Groq client with key from Streamlit secrets or environment
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
GROQ_MODEL = st.secrets.get("GROQ_MODEL") or os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant"

_groq_client = None
if GROQ_API_KEY and Groq is not None:
    _groq_client = Groq(api_key=GROQ_API_KEY)
else:
    # Surface actionable error if key or package missing when functions are called
    pass


def _require_groq():
    if Groq is None:
        st.error("Missing 'groq' package. Add 'groq' to requirements.txt and install dependencies.")
        raise RuntimeError("groq package not available")
    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY not found in Streamlit secrets or environment.")
        raise RuntimeError("GROQ_API_KEY missing")
    if _groq_client is None:
        raise RuntimeError("Groq client not initialized")
    return _groq_client


def _choices_content(resp) -> str:
    try:
        # groq SDK returns OpenAI-compatible structure
        content = resp.choices[0].message.get("content")  # type: ignore[attr-defined]
        if content is not None:
            return content
    except Exception:
        pass
    # Fallback for attribute-style access
    try:
        return resp.choices[0].message.content  # type: ignore[attr-defined]
    except Exception:
        return ""


def generate_skeleton_openai(email_text: str, student_summary: str = None) -> str:
    prompt = f"""
You are an assistant that creates a concise professional reply skeleton for an advisor responding to a student's email.

Student summary:
{student_summary or 'N/A'}

Incoming email:
{email_text}

Produce:
1) A subject suggestion (single line)
2) A short bullet-point skeleton for the reply (2-6 bullets)
3) Any recommended resources (URLs or names)
Return as JSON with keys: subject, bullets, resources
"""
    client = _require_groq()
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.2
    )

    return _choices_content(resp)

def critique_reply_openai(draft_text: str, original_email: str) -> str:
    prompt = f"""
You are an assistant that evaluates a reply draft vs an incoming email.

Incoming email:
{original_email}

Reply draft:
{draft_text}

Return a short JSON: {{ "answers_point": true/false, "issues": ["..."], "improvements": ["..."] }}
"""
    client = _require_groq()
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0
    )

    return _choices_content(resp)
