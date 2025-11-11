import streamlit as st
import pandas as pd
import plotly.express as px
import json, re
from PIL import Image
from io import BytesIO
import base64

from libs.sheets import load_sheet_as_df
from libs.nlp import classify_topic, detect_urgency, detect_sender_type
from libs.llm_client import generate_email_skeleton, fact_check_and_save
from libs.gmail_scheduler import get_scheduler


# ------------------------------------------------
# CONFIG
# ------------------------------------------------
st.set_page_config(
    page_title="BAKY TERPS - Academic Advisor Dashboard",
    layout="wide",
)

SHEET_ID = st.secrets.get("SHEET_ID")


# ------------------------------------------------
# THEME STYLING
# ------------------------------------------------
st.markdown(
    """
    <style>
        body, .main, .stApp {
            background-color: white !important;
            color: #000000;
            font-family: 'Calibri', sans-serif;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #000000;
            font-weight: 700;
        }
        .stat-card {
            border-radius: 15px;
            padding: 20px;
            background-color: white;
            border: 2px solid #E03A3E;
            margin-bottom: 15px;
            transition: transform 0.2s ease-in-out;
            box-shadow: 0px 3px 10px rgba(0,0,0,0.08);
        }
        .stat-card:hover {
            transform: scale(1.02);
            box-shadow: 0px 6px 18px rgba(0,0,0,0.15);
        }
        .stat-card-title {
            font-size: 16px;
            font-weight: 800;
            color: #E03A3E;
            margin-bottom: -5px;
        }
        .stat-card-value {
            font-size: 28px;
            font-weight: 800;
            color: #000000;
        }
        .stat-card-sub {
            font-size: 12px;
            color: #666666;
        }
        .chart-container {
            border-radius: 18px;
            background-color: white;
            padding: 15px 20px 10px 20px;
            border: 1.5px solid rgba(224,58,62,0.25);
            box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            margin-bottom: 25px;
        }
        .chart-container:hover {
            box-shadow: 0px 8px 20px rgba(0,0,0,0.12);
            transform: scale(1.005);
            transition: 0.2s ease-in-out;
        }
        .custom-info-box {
            background-color: #FFF9E6;
            border-radius: 12px;
            padding: 15px 20px;
            margin-bottom: 20px;
            border-left: 4px solid #FFD520;
            font-size: 15px;
            color: #856404;
        }
        .custom-info-box::before {
            content: "✍️ ";
            margin-right: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ------------------------------------------------
# HEADER WITH LOGO AND TITLE
# ------------------------------------------------
def image_to_base64(img_path):
    img = Image.open(img_path).convert("RGBA")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


logo_b64 = image_to_base64("testudo.jpg")

header_html = f"""
<div style="display:flex;align-items:center;justify-content:center;margin-top:-15px;margin-bottom:25px;">
    <img src="data:image/png;base64,{logo_b64}" width="85" style="margin-right:18px;">
    <h1 style="color:#E03A3E;font-weight:900;font-style:italic;font-size:44px;letter-spacing:1px;">
        BAKY TERPS - Academic Advisor
    </h1>
</div>
"""
# Extra CSS to ensure consistent light theme across all widgets
st.markdown(
    """
    <style>
        /* Sidebar */
        [data-testid=\"stSidebar\"] { background-color: #ffffff !important; }
        [data-testid=\"stSidebar\"] * { color: #000000 !important; }

        /* Buttons */
        .stButton > button {
            background-color: #E03A3E !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 700 !important;
        }
        .stButton > button:hover {
            background-color: #c63437 !important;
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(224,58,62,0.35);
        }

        /* Inputs */
        div[data-baseweb=\"input\"] input,
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #dcdcdc !important;
            border-radius: 8px !important;
        }
        div[data-baseweb=\"input\"] input::placeholder,
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder { color: #666666 !important; }

        /* Select / Multiselect */
        div[data-baseweb=\"select\"] > div {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #dcdcdc !important;
            border-radius: 8px !important;
        }
        .stApp [role=\"listbox\"] {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #dcdcdc !important;
            border-radius: 8px !important;
        }
        .stApp [role=\"listbox\"] [role=\"option\"] { color: #000000 !important; }
        .stApp [role=\"listbox\"] [role=\"option\"][aria-selected=\"true\"],
        .stApp [role=\"listbox\"] [role=\"option\"]:hover { background-color: #FFF0F0 !important; }

        /* Tables (st.table) */
        div[data-testid=\"stTable\"] table {
            background-color: #ffffff !important;
            color: #000000 !important;
            border-collapse: collapse !important;
        }
        div[data-testid=\"stTable\"] thead th {
            background-color: #f6f6f6 !important;
            color: #000000 !important;
            border-bottom: 1px solid #e6e6e6 !important;
        }
        div[data-testid=\"stTable\"] tbody td {
            background-color: #ffffff !important;
            color: #000000 !important;
            border-bottom: 1px solid #f0f0f0 !important;
        }

        /* DataFrame (st.dataframe) */
        div[data-testid=\"stDataFrame\"],
        section[data-testid=\"stDataFrame\"] {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #eaeaea !important;
            border-radius: 10px !important;
            overflow: hidden;
            /* Override Streamlit theme vars inside the dataframe scope */
            --text-color: #000000 !important;
            --background-color: #ffffff !important;
            --secondary-background-color: #f6f6f6 !important;
            --primary-color: #E03A3E !important;
            --border-color: #eaeaea !important;
        }
        div[data-testid=\"stDataFrame\"] *,
        section[data-testid=\"stDataFrame\"] * { color: #000000 !important; }
        div[data-testid=\"stDataFrame\"] table,
        section[data-testid=\"stDataFrame\"] table { background-color: #ffffff !important; }
        div[data-testid=\"stDataFrame\"] thead th,
        section[data-testid=\"stDataFrame\"] thead th {
            background-color: #f6f6f6 !important;
            color: #000000 !important;
            border-bottom: 1px solid #e6e6e6 !important;
        }
        div[data-testid=\"stDataFrame\"] tbody td,
        section[data-testid=\"stDataFrame\"] tbody td {
            background-color: #ffffff !important;
            color: #000000 !important;
            border-bottom: 1px solid #f0f0f0 !important;
        }

        /* Expanders */
        [data-testid=\"stExpander\"] > div {
            background-color: #ffffff !important;
            border: 1px solid rgba(224,58,62,0.25) !important;
            border-radius: 12px !important;
        }
        [data-testid=\"stExpander\"] summary {
            color: #000000 !important;
            font-weight: 700 !important;
        }

        /* Markdown tables */
        .stMarkdown table { background-color: #ffffff !important; border-collapse: collapse !important; }
        .stMarkdown th, .stMarkdown td { color: #000000 !important; border: 1px solid #efefef !important; }

        /* Links & dividers */
        a, a:visited { color: #E03A3E !important; }
        hr { border-color: #efefef !important; }

        /* Checkboxes, radios, sliders */
        .stCheckbox, .stRadio { color: #000000 !important; }
        .stSlider [data-baseweb=\"slider\"] { color: #000000 !important; }

        /* File uploader */
        [data-testid=\"stFileUploader\"] section[tabindex] {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px dashed #dcdcdc !important;
            border-radius: 10px !important;
        }

        /* Fix info box icon text */
        .custom-info-box::before { content: "ℹ️ "; }
    </style>
    """,
    unsafe_allow_html=True
)

# Inject overrides for expander, alerts, and code visibility
st.markdown(
    """
    <style>
        /* Ensure expander header is light and readable */
        [data-testid=\"stExpander\"] summary {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid rgba(224,58,62,0.25) !important;
            border-radius: 10px !important;
        }
        [data-testid=\"stExpander\"] summary svg { color: #000000 !important; fill: #000000 !important; }
        [data-testid=\"stExpander\"] > div { background-color: #ffffff !important; }

        /* Make alerts readable on light background */
        [data-testid=\"stAlert\"] {
            background-color: #FFF9E6 !important;
            color: #000000 !important;
            border-left: 4px solid #FFD520 !important;
            border-radius: 10px !important;
        }
        [data-testid=\"stAlert\"] * { color: #000000 !important; }

        /* Make code blocks visible (fact-check report, templates) */
        div[data-testid=\"stCodeBlock\"] { background-color: #f8f8f8 !important; color: #111111 !important; border-radius: 8px !important; }
        div[data-testid=\"stCodeBlock\"] pre { background-color: #f8f8f8 !important; color: #111111 !important; }
        pre, code { background-color: #f8f8f8 !important; color: #111111 !important; }

        /* Force info icon text to correct glyph */
        .custom-info-box::before { content: \"ℹ️ \" !important; }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(header_html, unsafe_allow_html=True)

# Final tiny CSS fixups (ASCII-escaped to avoid encoding issues)
st.markdown(
    """
    <style>
        /* Force info icon glyph with CSS escape */
        .custom-info-box::before { content: "\2139\FE0F "; }
    </style>
    """,
    unsafe_allow_html=True
)


# ------------------------------------------------
# START BACKGROUND GMAIL SYNC
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
# SIDEBAR NAVIGATION
# ------------------------------------------------
st.sidebar.title("📊 Navigation")

page = st.sidebar.radio(
    "Go to:",
    ["Home Dashboard", "Students", "Emails", "Meetings", "Policies"]
)

# Gmail Sync Status
scheduler = get_scheduler()
status = scheduler.get_status()

st.sidebar.markdown("### 📩 Gmail Sync Status")
st.sidebar.write("✅ Running:", status["is_running"])
st.sidebar.write("⏱ Last Sync:", status["last_sync_time"])
st.sidebar.write("📥 Emails Added:", status["last_sync_count"])
st.sidebar.write("⏭ Next Run:", status["next_run_time"])

if st.sidebar.button("🔄 Run Gmail Sync Now"):
    scheduler.sync_emails()
    st.sidebar.success("✅ Sync complete!")


# ------------------------------------------------
# LOAD GOOGLE SHEETS DATA
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
# HELPER: STAT CARD
# ------------------------------------------------
def stat_card(title, value, subtitle=""):
    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-card-title">{title}</p>
            <h2 class="stat-card-value">{value}</h2>
            <p class="stat-card-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ================================================================
# HOME DASHBOARD
# ================================================================
if page == "Home Dashboard":
    total_students = len(student_cases)
    scheduled_meetings = len(meetings)
    student_cases["GPA"] = pd.to_numeric(student_cases["GPA"], errors="coerce")
    avg_gpa = round(student_cases["GPA"].mean(), 2) if student_cases["GPA"].notna().any() else "N/A"
    priority_alerts = len(policies[policies["Probation"] == "Yes"])
    graduating = len(student_cases[student_cases["Predicted Graduation"] == "F25"])

    c1, c2, c3, c4 = st.columns(4)
    with c1: stat_card("Total Students", total_students)
    with c2: stat_card("This Week", scheduled_meetings)
    with c3: stat_card("Avg GPA", avg_gpa)
    with c4: stat_card("Priority Alerts", priority_alerts)

    st.markdown("---")

    st.subheader("🎓 Student & Email Insights")
    c1, c2 = st.columns(2)

    # --- Students by Program ---
    with c1:
        st.markdown("### Students by Program")
        if "Program" in student_cases.columns:
            program_counts = student_cases["Program"].value_counts()
            fig = px.pie(values=program_counts, names=program_counts.index,
                         color_discrete_sequence=["#E03A3E", "#FFD520", "#000000"])
            fig.update_layout(
                font=dict(color="black"),
                legend=dict(font=dict(color="black")),
                paper_bgcolor="white",
                plot_bgcolor="white"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Emails by Category ---
    with c2:
        st.markdown("### Emails by Category")
        if "topic" in email_df.columns:
            topic_counts = email_df["topic"].value_counts().reset_index()
            topic_counts.columns = ["Topic", "Count"]
            fig = px.bar(topic_counts, x="Topic", y="Count", color="Topic",
                         color_discrete_sequence=["#E03A3E", "#FFD520", "#000000"])
            fig.update_layout(
                font=dict(color="black"),
                legend=dict(font=dict(color="black")),
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                xaxis=dict(
                    tickfont=dict(color="black"),
                    title_font=dict(color="black"),
                    gridcolor="lightgray",
                    linecolor="black"
                ),
                yaxis=dict(
                    tickfont=dict(color="black"),
                    title_font=dict(color="black"),
                    gridcolor="lightgray",
                    linecolor="black"
                )
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("---")

    # --- Credits Distribution ---
    st.subheader("📘 Credits Distribution")
    if "Earned Credits" in student_cases.columns:
        bins = [0, 10, 20, 30, 40, 50, 60, 80, 100]
        labels = ["0–10", "11–20", "21–30", "31–40", "41–50", "51–60", "61–80", "80+"]
        student_cases["credit_bin"] = pd.cut(
            pd.to_numeric(student_cases["Earned Credits"], errors="coerce"),
            bins=bins, labels=labels, include_lowest=True
        )
        credit_counts = student_cases["credit_bin"].value_counts().reset_index()
        credit_counts.columns = ["Range", "Count"]
        fig = px.bar(credit_counts, x="Range", y="Count", color="Range",
                     color_discrete_sequence=["#E03A3E", "#FFD520", "#000000"])
        fig.update_layout(
            #title_font=dict(color="black", size=18),
            font=dict(color="black"),
            legend=dict(font=dict(color="black")),
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False,
            xaxis=dict(
                tickfont=dict(color="black"),
                title_font=dict(color="black"),
                gridcolor="lightgray",
                linecolor="black"
            ),
            yaxis=dict(
                tickfont=dict(color="black"),
                title_font=dict(color="black"),
                gridcolor="lightgray",
                linecolor="black"
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- GPA Distribution ---
    st.subheader("🎯 GPA Distribution")
    bins = [0, 2.5, 3.0, 3.5, 4.1]
    labels = ["Below 2.5", "2.5–2.99", "3.0–3.49", "3.5–4.0"]
    student_cases["GPA_bin"] = pd.cut(student_cases["GPA"], bins=bins, labels=labels)
    gpa_counts = student_cases["GPA_bin"].value_counts().reset_index()
    gpa_counts.columns = ["GPA Range", "Count"]
    fig = px.bar(gpa_counts, x="Count", y="GPA Range", orientation="h",
                 color_discrete_sequence=["#E03A3E"])
    fig.update_layout(
        font=dict(color="black"),
        legend=dict(font=dict(color="black")),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
            gridcolor="lightgray",
            linecolor="black"
        ),
        yaxis=dict(
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
            gridcolor="lightgray",
            linecolor="black"
        )
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- Academic Alerts ---
    st.subheader("⚠️ Academic Policy Alerts")
    alerts = policies[
        (policies["Probation"] == "Yes") |
        (policies["Registration Block"] == "Yes")
    ]
    for _, row in alerts.iterrows():
        st.write(f"**{row['Student']}** — UID: {row['UID']}")
        st.caption(row.get("Note", ""))

    st.markdown("---")

    # --- AI EMAIL ASSISTANT ---
    st.subheader("🧠 AI Email Draft Assistant")
    newest = email_df.sort_values("Date", ascending=False).head(5)
    for idx, row in newest.iterrows():
        with st.expander(f"📧 {row['Name']} — {row['Subject']}"):
            st.write(f"**From:** {row['Email']}")
            st.write(f"**Date:** {row['Date'].strftime('%b %d, %Y') if pd.notnull(row['Date']) else 'N/A'}")
            st.markdown("**Content:**")
            st.write(row['Content'])
            st.markdown("---")

            if st.button(f"🪄 Generate AI Skeleton #{idx}", key=f"skeleton_btn_{idx}"):
                with st.spinner("Generating AI reply skeleton..."):
                    skeleton_json = generate_email_skeleton(row["Content"], student_summary=row.get("Name", "N/A"))
                st.session_state[f"skeleton_json_{idx}"] = skeleton_json

            if f"skeleton_json_{idx}" in st.session_state:
                raw_output = st.session_state[f"skeleton_json_{idx}"]
                try:
                    match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                    cleaned_json = match.group(0) if match else raw_output
                    skeleton = json.loads(cleaned_json)
                except Exception:
                    st.warning("⚠️ Could not parse Groq output as JSON.")
                    st.code(raw_output)
                    continue

                st.markdown("### ✉️ AI-Generated Reply Skeleton")
                st.write("**Summary:**", skeleton.get("summary", ""))
                st.markdown("**Points to Include:**")
                for point in skeleton.get("reply_points", []):
                    st.markdown(f"- {point}")
                if skeleton.get("suggested_links"):
                    st.markdown("**Useful Links:**")
                    for link in skeleton["suggested_links"]:
                        st.markdown(f"- [{link}]({link})")
                st.markdown("**Template Reply:**")
                st.code(skeleton.get("skeleton_reply", ""), language="markdown")

                st.markdown('<div class="custom-info-box">Write your own email below based on this skeleton:</div>', unsafe_allow_html=True)
                user_draft = st.text_area("Your Email Draft", key=f"user_draft_{idx}", height=220)

                if st.button(f"✅ Fact-check & Save Draft #{idx}", key=f"factcheck_btn_{idx}"):
                    if not user_draft.strip():
                        st.warning("⚠️ Please write your draft before fact-checking.")
                    else:
                        with st.spinner("Fact-checking your reply..."):
                            review = fact_check_and_save(user_draft, st.session_state[f"skeleton_json_{idx}"], row["Content"])
                        st.markdown("**📋 Fact-check Report:**")
                        st.code(review, language="json")


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
    st.dataframe(results, use_container_width=True, height=520)


# ================================================================
# EMAILS
# ================================================================
elif page == "Emails":
    st.title("Emails")
    st.dataframe(email_df.sort_values("Date", ascending=False), use_container_width=True, height=520)


# ================================================================
# MEETINGS
# ================================================================
elif page == "Meetings":
    st.title("Advisor Meetings")
    st.dataframe(meetings, use_container_width=True, height=520)


# ================================================================
# POLICIES
# ================================================================
elif page == "Policies":
    st.title("Policy Records")
    st.dataframe(policies, use_container_width=True, height=520)
