# 📧 Email Agent — Streamlit AI Assistant

The **Email Agent** is a Streamlit-based application designed to help the **Master’s Program Office** manage student communication efficiently.  
It connects Gmail and Google Sheets with an AI engine (OpenAI or Grok) to **analyze emails**, **log data**, and **draft context-aware replies** automatically.  

---

## 🧩 Key Functionalities

### 1. **Email Ingestion**
- Fetches unread or specific emails from Gmail using the Gmail API.
- Extracts sender, subject, message body, and timestamps.
- Stores the data in a structured DataFrame for processing.

### 2. **Google Sheets Integration**
- Syncs with Google Sheets via a service account (`service_account.json`).
- Automatically logs new emails under the **Student Cases** sheet.
- Supports reading and writing to multiple worksheets (e.g., `student cases`, `email history`).

### 3. **AI-Powered Draft Generation**
- Uses an LLM client (`libs/llm_client.py`) to generate **draft or skeleton email replies**.
- Supports multiple LLM providers:
  - ✅ **OpenAI GPT models** (default)
  - 🧠 **Grok / open-source LLMs** (configurable alternative)
- Contextually summarizes and replies to student queries with relevant links or resources.

### 4. **Dashboard Analytics**
- Visualizes metrics such as:
  - Average response times  
  - Urgency breakdown  
  - Student case status  
  - AI draft quality (if tracked)
- Allows the user to filter, view, and manage records interactively.

---

## 🗂️ Project Structure

```bash
email_agent/
│
├── app.py                     # Main Streamlit dashboard and UI logic
│
├── libs/
│   ├── gmail_to_sheets.py     # Handles Gmail API and Google Sheets sync
│   ├── llm_client.py          # Connects to OpenAI / Grok to generate drafts
│   ├── sheet_utils.py         # Sheet helper functions (read/write)
│   └── utils.py               # Common functions (cleaning, parsing, etc.)
│
├── .streamlit/
│   └── secrets.toml           # Stores API keys, sheet IDs, and credentials
│
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation (this file)
└── venv/                      # Local virtual environment (ignored in Git)
⚙️ Setup Instructions
1. Clone the Repository
bash
Copy code
git clone https://github.com/<yourusername>/email_agent.git
cd email_agent
2. Create a Virtual Environment
bash
Copy code
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # macOS/Linux
3. Install Dependencies
bash
Copy code
pip install -r requirements.txt
4. Configure Secrets
In .streamlit/secrets.toml:

toml
Copy code
[google]
service_account = "path/to/service_account.json"
sheet_id = "your-google-sheet-id"

[gmail]
token_path = "token.json"
credentials_path = "credentials.json"

[llm]
provider = "openai"          # or "grok"
api_key = "sk-xxxxxxxxxx"
⚠️ Never commit secrets.toml — add it to .gitignore.

5. Run the App
bash
Copy code
streamlit run app.py
🧠 Functional Flow Overview
text
Copy code
┌──────────────┐
│   Gmail API  │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│ Email Extraction    │
│ (gmail_to_sheets.py)│
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Google Sheets Sync  │
│ (sheet_utils.py)    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ LLM Draft Generator │
│ (llm_client.py)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Streamlit Dashboard │
│ (app.py)            │
└─────────────────────┘
🎨 Dashboard Customization Guide
Your Streamlit dashboard can be styled and re-themed easily.
Below are tips and snippets to personalize the layout.

🖋️ 1. Change Font
Add this to your app.py before Streamlit components:

python
Copy code
st.markdown(
    """
    <style>
    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
)
Replace 'Poppins' with any Google Font.

🌈 2. Change Colors
You can set primary and background colors using Streamlit’s theme config.

In .streamlit/config.toml:

toml
Copy code
[theme]
primaryColor = "#4F46E5"
backgroundColor = "#F9FAFB"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#111827"
font = "sans serif"
Restart Streamlit after saving.

🧱 3. Layout Design Tips
Goal	Code Snippet	Notes
Two-column layout	col1, col2 = st.columns(2)	Use for summary stats and charts side-by-side
Center align widgets	st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)	Helps with visual balance
Use expanders for sections	with st.expander("View Details"):	Keeps dashboard clean
Add tabs for navigation	tab1, tab2 = st.tabs(["Dashboard", "Logs"])	Great for switching between analytics and raw data
Add logo or header	st.image("assets/logo.png", width=120)	Place branding at the top

📊 4. Designing Effective Analytics
Keep it minimal: Avoid overcrowding with too many metrics.

Use color psychology: Red for urgency, green for resolved, blue for neutral actions.

Interactive filters: Add dropdowns or sliders for dates and urgency levels.

Use tooltips: Help users interpret metrics clearly.

🧰 Developer Notes
When switching from OpenAI to Grok, update:

toml
Copy code
[llm]
provider = "grok"
api_key = "your-grok-key"
And edit libs/llm_client.py to load the relevant API client.

Add custom logic for new analytics in app.py under the "Dashboard Metrics" section.

Log errors and API timeouts gracefully — Streamlit’s st.error() helps display readable messages.

To clean or rebuild data:

bash
Copy code
python libs/gmail_to_sheets.py
🚀 Future Enhancements
Email intent classification (urgent, info, query, complaint)

Sentiment tracking for responses

Integration with Microsoft Outlook / Teams

Dashboard export as PDF

Role-based login for multiple staff

🧑‍💻 Author
Ajay Sumukh
📍 Built for process automation and intelligent email management using Streamlit and AI.
💡 "Turning inbox chaos into organized insight."

🪪 License
MIT License — Free for modification and distribution with attribution.

yaml
Copy code

---

Would you like me to also generate a **`config.toml`** and **custom CSS snippet** that perfectly match your
