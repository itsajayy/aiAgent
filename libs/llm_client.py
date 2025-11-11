import os
import streamlit as st
from groq import Groq
import gspread
from google.oauth2.service_account import Credentials

# === GROQ SETUP ===
GROQ_API_KEY = (
    st.secrets.get("GROQ_API")
    or st.secrets.get("GROQ_API_KEY")
    or os.getenv("GROQ_API")
    or os.getenv("GROQ_API_KEY")
)

if not GROQ_API_KEY:
    st.error("GROQ API key not found. Set GROQ_API or GROQ_API_KEY in secrets or env.")
    raise RuntimeError("Missing GROQ API key")

client = Groq(api_key=GROQ_API_KEY)


# === GOOGLE SHEETS SETUP ===
# Requires Streamlit secrets: "google_credentials" and "SHEET_ID"
def connect_to_sheet():
    """Connect to Google Sheets using service account from secrets.

    Supports either `google_credentials` or `gcp_service_account` keys
    inside `.streamlit/secrets.toml`.
    """
    try:
        svc_info = (
            st.secrets.get("google_credentials")
            or st.secrets.get("gcp_service_account")
        )
        if not svc_info:
            raise KeyError(
                'Missing service account in secrets. Add either "google_credentials" or "gcp_service_account".'
            )

        creds = Credentials.from_service_account_info(
            svc_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gs_client = gspread.authorize(creds)
        sheet_id = st.secrets["SHEET_ID"]
        return gs_client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        raise


# === FUNCTION 1: Generate Email Skeleton ===
def generate_email_skeleton(email_text: str, student_summary: str = None) -> str:
    """
    Generates a structured skeleton for a reply:
    - Summarizes the email
    - Lists what to include in the reply
    - Suggests useful links/resources
    - Adds a placeholder for the user’s draft
    """
    prompt = f"""
You are an academic assistant who helps advisors draft responses to student emails.

Student summary:
{student_summary or 'N/A'}

Incoming email:
{email_text}

Generate a JSON response with:
1. "summary": A concise summary of the student's email (2-3 sentences)
2. "reply_points": Bullet points of what the advisor should include in their reply
3. "suggested_links": A list of URLs or resources based on the student's question
4. "skeleton_reply": A short draft layout the user can fill in (with placeholders like {{student_name}}, {{resource_link}})
5. "user_draft_space": A message prompting the user to input their final draft

Example JSON structure:
{{
  "summary": "...",
  "reply_points": ["...", "..."],
  "suggested_links": ["...", "..."],
  "skeleton_reply": "Hi {{student_name}},\\nThank you for reaching out...\\nRegards,\\n{{advisor_name}}",
  "user_draft_space": "✍️ Please type your final draft below."
}}
"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a helpful academic assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=600,
        temperature=0.3,
    )

    return resp.choices[0].message.content


# Backwards-compatible alias expected by app.py
def generate_skeleton_openai(email_text: str, student_summary: str = None) -> str:
    return generate_email_skeleton(email_text, student_summary)


# === FUNCTION 2: Fact Check and Save ===
def fact_check_and_save(user_draft: str, skeleton: str, email_text: str):
    """
    Fact-checks the user's draft against the skeleton + original email,
    and saves it to Google Sheets if it passes.
    """
    prompt = f"""
You are a precise fact-checker.

Compare the following:

Original Email:
{email_text}

Generated Skeleton:
{skeleton}

User Draft:
{user_draft}

Evaluate:
- Does the user draft address the main points from the skeleton?
- Is it factually consistent with the student's original email?
- Does it maintain a polite and professional tone?

Return a JSON:
{{
  "factually_correct": true/false,
  "missing_points": ["..."],
  "incorrect_info": ["..."],
  "tone_feedback": "..."
}}
"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a strict and helpful reviewer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
        temperature=0.2,
    )

    result = resp.choices[0].message.content

    # Save to Google Sheets only if factually_correct = true
    if '"factually_correct": true' in result.lower():
        try:
            sheet = connect_to_sheet().worksheet("drafts")
        except gspread.WorksheetNotFound:
            sheet = connect_to_sheet().add_worksheet(title="drafts", rows=1000, cols=10)

        sheet.append_row([email_text, skeleton, user_draft, result])
        st.success("✅ Draft verified and saved to Google Sheets!")
    else:
        st.warning("⚠️ Draft not factually correct. Please revise before saving.")

    return result
