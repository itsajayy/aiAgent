


## 🧩 Project Structure
<img width="648" height="564" alt="image" src="https://github.com/user-attachments/assets/556646c8-7398-42e7-9a64-cfcd554436a9" />


## 🧠 How It Works — Step-by-Step Workflow

### 1️⃣ Data Integration (Google Sheets)
- The app connects to **4 Google Sheets** for data retrieval:
  1. **Student Cases** → student info, credits, GPA  
  2. **Meetings** → advisor-student meeting records  
  3. **Academic Policies** → registration blocks, probation  
  4. **Email History** → all sent/received emails and AI responses  

- The connection uses a **Google Service Account** defined in `.streamlit/secrets.toml`.

---

### 2️⃣ AI Draft Generation
When a new email arrives:
1. The text is sent to the **OpenAI API** via the `generate_skeleton_openai()` function.
2. GPT creates a **skeleton draft** — concise, polite, and professional.
3. The draft is displayed alongside recommended resources.

---

### 3️⃣ Draft Evaluation
After the user reviews or edits the draft:
1. The draft and original email are sent to `critique_reply_openai()`.
2. The AI provides a **brief evaluation**:
   - Tone (politeness, professionalism)
   - Completeness (did it address the query?)
   - Grammar and clarity

---

### 4️⃣ Student Insights
If the sender is a student (recognized by email domain):
- The system fetches their profile data from the Google Sheets.
- The user can open a full dashboard with GPA history, notes, and holds.

---

### 5️⃣ Dashboard Analytics
Aggregates and visualizes:
- Email count, trends, and urgency
- AI vs manual handling
- Hours saved
- Most discussed topics
- Categorized monthly email trends

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/email_agent.git
cd email_agent

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

always run in an virtual environment
streamlit run app.py


