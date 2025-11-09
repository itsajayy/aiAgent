# libs/llm_client.py
import os
import streamlit as st
from openai import OpenAI



# Initialize OpenAI client with key from Streamlit secrets or environment
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets. Please add it to .streamlit/secrets.toml")
    raise


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
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.2
    )

    return resp.choices[0].message["content"]

def critique_reply_openai(draft_text: str, original_email: str) -> str:
    prompt = f"""
You are an assistant that evaluates a reply draft vs an incoming email.

Incoming email:
{original_email}

Reply draft:
{draft_text}

Return a short JSON: {{ "answers_point": true/false, "issues": ["..."], "improvements": ["..."] }}
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0
    )

    return resp.choices[0].message["content"]
