import streamlit as st
import pandas as pd
import plotly.express as px

from libs.sheets import load_sheet_as_df
from libs.nlp import classify_topic, detect_urgency, detect_sender_type
from libs.llm_client import generate_skeleton_openai
from libs.gmail_scheduler import get_scheduler


# ------------------------------------------------
# CONFIG
# ------------------------------------------------
st.set_page_config(
    page_title="AI Academic Advisor Dashboard",
    layout="wide",
)

SHEET_ID = st.secrets.get("SHEET_ID")


# ------------------------------------------------
# START BACKGROUND GMAIL SYNC (only once)
# ------------------------------------------------
if "scheduler_started" not in st.session_state:
    try:
        scheduler = get_scheduler()
        scheduler.start(interval_minutes=4)
        st.session_state["scheduler_started"] = True
        print("✅ Gmail scheduler started")
    except Exception as e:
        print("⚠️ Failed to start scheduler:", e)


# ------------------------------------------------
# SIDEBAR NAV + SYNC STATUS
# ------------------------------------------------
st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to:",
    ["Home Dashboard", "Students", "Emails", "Meetings", "Policies"]
)

# Show scheduler status
scheduler = get_scheduler()
status = scheduler.get_status()

st.sidebar.markdown("### 📩 Gmail Sync Status")
st.sidebar.write("✅ Running:", status["is_running"])
st.sidebar.write("⏱ Last Sync:", status["last_sync_time"])
st.sidebar.write("📥 Emails Added:", status["last_sync_count"])
st.sidebar.write("⏭ Next Run:", status["next_run_time"])

# Manual sync button
if st.sidebar.button("🔄 Run Gmail Sync Now"):
    scheduler.sync_emails()
    st.sidebar.success("✅ Sync complete!")


# ------------------------------------------------
# LOAD SHEETS
# ------------------------------------------------
student_cases = load_sheet_as_df(SHEET_ID, "Student Case")
meetings = load_sheet_as_df(SHEET_ID, "Meetings")
policies = load_sheet_as_df(SHEET_ID, "Academic Policy")
email_df = load_sheet_as_df(SHEET_ID, "Email")


# ------------------------------------------------
# PREPROCESS EMAIL DATA
# ------------------------------------------------
email_df["Date"] = pd.to_datetime(email_df["Date"], errors="coerce")
email_df["month"] = email_df["Date"].dt.strftime("%b")

email_df["topic"] = email_df["Content"].apply(classify_topic)
email_df["urgency"] = email_df["Content"].apply(detect_urgency)
email_df["sender_type"] = email_df["Email"].apply(detect_sender_type)


# ------------------------------------------------
# CARD UI
# ------------------------------------------------
def stat_card(title, value, subtitle=""):
    st.markdown(
        f"""
        <div style="border-radius:10px;padding:20px;background:white;
        border:1px solid #eee;margin-bottom:12px;">
            <p style="color:#666;margin-bottom:-5px;font-size:14px;">{title}</p>
            <h2 style="margin:0;color:#111;">{value}</h2>
            <p style="font-size:12px;color:#999;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ================================================================
# HOME DASHBOARD
# ================================================================
if page == "Home Dashboard":
    st.title("Academic Advising & Email Insights")

    # --- TOP CARDS ---
    total_students = len(student_cases)
    scheduled_meetings = len(meetings)

    # GPA handling
    student_cases["GPA"] = pd.to_numeric(student_cases["GPA"], errors="coerce")
    avg_gpa = round(student_cases["GPA"].mean(), 2) if student_cases["GPA"].notna().any() else "N/A"

    priority_alerts = len(policies[policies["Probation"] == "Yes"])
    graduating = len(student_cases[student_cases["Predicted Graduation"].notna()])

    c1, c2, c3 = st.columns(3)
    with c1:
        stat_card("Total Students", total_students)
    with c2:
        stat_card("This Week", scheduled_meetings)
    with c3:
        stat_card("Avg GPA", avg_gpa)

    c4, c5 = st.columns(2)
    with c4:
        stat_card("Priority Alerts", priority_alerts)
    with c5:
        stat_card("Graduating", graduating)

    st.markdown("---")

    # --- Students by Program ---
    st.subheader("Students by Program")
    if "Program" in student_cases.columns:
        program_counts = student_cases["Program"].value_counts()
        fig = px.pie(values=program_counts, names=program_counts.index)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Credits Distribution ---
    st.subheader("Credits Distribution")
    if "Earned Credits" in student_cases.columns:
        bins = [0, 30, 60, 90, 120, 999]
        labels = ["0–30", "31–60", "61–90", "91–120", "120+"]

        student_cases["credit_bin"] = pd.cut(
            pd.to_numeric(student_cases["Earned Credits"], errors="coerce"),
            bins=bins,
            labels=labels,
            include_lowest=True
        )
        credit_counts = student_cases["credit_bin"].value_counts().reset_index()
        credit_counts.columns = ["Range", "Count"]

        fig = px.bar(credit_counts, x="Range", y="Count")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- GPA Distribution ---
    st.subheader("GPA Distribution")

    bins = [0, 2.5, 3.0, 3.5, 4.1]
    labels = ["Below 2.5", "2.5–2.99", "3.0–3.49", "3.5–4.0"]

    student_cases["GPA_bin"] = pd.cut(student_cases["GPA"], bins=bins, labels=labels)
    gpa_counts = student_cases["GPA_bin"].value_counts().reset_index()
    gpa_counts.columns = ["GPA Range", "Count"]

    fig = px.bar(gpa_counts, x="Count", y="GPA Range", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Academic Alerts ---
    st.subheader("Academic Policy Alerts")
    alerts = policies[
        (policies["Probation"] == "Yes") |
        (policies["Registration Block"] == "Yes")
    ]

    for _, row in alerts.iterrows():
        st.write(f"**{row['Student']}** — UID: {row['UID']}")
        st.caption(row.get("Note", ""))

    st.markdown("---")

    # --- Recent Emails ---
    st.subheader("Recent Emails")

    newest = email_df.sort_values("Date", ascending=False).head(5)
    for idx, row in newest.iterrows():
        with st.expander(f"{row['Name']} — {row['Subject']}"):
            st.write("**Email:**", row['Email'])
            st.write("**Date:**", row['Date'])
            st.write("**Content:**")
            st.write(row['Content'])

            if st.button(f"Generate Draft #{idx}", key=f"draft_{idx}"):
                draft = generate_skeleton_openai(row['Content'])
                st.code(draft)


# ================================================================
# STUDENTS
# ================================================================
elif page == "Students":
    st.title("Students")

    query = st.text_input("Search by name or UID")

    results = student_cases[
        student_cases["Student"].str.contains(query, case=False, na=False) |
        student_cases["UID"].astype(str).str.contains(query, case=False, na=False)
    ] if query else student_cases

    st.dataframe(results)


# ================================================================
# EMAILS
# ================================================================
elif page == "Emails":
    st.title("Emails")
    st.dataframe(email_df.sort_values("Date", ascending=False))


# ================================================================
# MEETINGS
# ================================================================
elif page == "Meetings":
    st.title("Advisor Meetings")
    st.dataframe(meetings)


# ================================================================
# POLICIES
# ================================================================
elif page == "Policies":
    st.title("Policy Records")
    st.dataframe(policies)
