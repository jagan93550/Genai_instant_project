# 🎓 AI Interview Coach for MCA Students

An offline, AI-powered mock interview coach built for MCA placement preparation.
It conducts a structured, multi-topic mock interview entirely on your own
machine using a local open-source LLM via **Ollama** — no API keys, no
internet dependency for the AI itself, no per-token cost.

---

## 1. Architecture

```
┌─────────────────────────┐
│        app.py            │   Streamlit UI (chat interface, sidebar, report view)
│   (Frontend — no logic)  │
└────────────┬─────────────┘
             │ calls only
             ▼
┌─────────────────────────┐
│  backend/interview_engine │  Orchestrates the interview: question order,
│         .py                │  follow-up decisions, progress tracking
└──────┬───────────┬────────┘
       │           │
       ▼           ▼
┌─────────────┐ ┌───────────────────┐
│ backend/     │ │ backend/evaluator  │
│ llm_client.py│ │       .py          │  Scores answers, applies rule-based
│ (Ollama I/O) │ │                    │  safety nets on top of LLM judgement
└──────┬───────┘ └───────────────────┘
       │
       ▼
┌─────────────────┐        ┌──────────────────────┐
│   Ollama Server   │        │ backend/database.py   │
│ (local LLM runtime)│        │ (SQLite persistence)  │
└─────────────────┘        └──────────────────────┘
                                       ▲
                                       │
                         backend/report_generator.py
                         (aggregates scores + LLM summary)
```

**Design principles applied:**
- **Separation of concerns** — UI (`app.py`) never touches SQL or the LLM directly.
- **Single responsibility** — one module per concern (DB, LLM, evaluation, orchestration, reporting).
- **Graceful degradation** — if Ollama is slow/unreachable, the app falls back to a static question bank instead of crashing.
- **Config-driven** — model name, categories, and thresholds live in `config.py`, not scattered across files.

---

## 2. Folder Structure

```
ai-interview-coach/
├── app.py                      # Streamlit entry point (run this file)
├── config.py                   # Central configuration
├── requirements.txt
├── .gitignore
├── README.md
├── backend/
│   ├── __init__.py
│   ├── database.py             # SQLite schema + CRUD
│   ├── llm_client.py           # Ollama integration
│   ├── question_bank.py        # Static fallback questions
│   ├── evaluator.py            # Scoring + follow-up decision logic
│   ├── interview_engine.py     # Core orchestrator
│   └── report_generator.py     # Final report builder
├── prompts/
│   ├── __init__.py
│   └── system_prompt.py        # All LLM prompt templates
├── utils/
│   ├── __init__.py
│   └── helpers.py               # JSON extraction, score clamping, IDs
└── data/
    └── interview_history.db     # Created automatically on first run
```

---

## 3. Database Schema

```sql
CREATE TABLE sessions (
    session_id   TEXT PRIMARY KEY,
    student_name TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    status       TEXT NOT NULL DEFAULT 'in_progress'
);

CREATE TABLE qa_log (
    qa_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT NOT NULL REFERENCES sessions(session_id),
    category            TEXT NOT NULL,
    question            TEXT NOT NULL,
    answer              TEXT NOT NULL,
    technical_score     INTEGER,
    communication_score INTEGER,
    confidence_score    INTEGER,
    feedback            TEXT,
    is_follow_up        INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL
);

CREATE TABLE reports (
    report_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id         TEXT NOT NULL REFERENCES sessions(session_id),
    avg_technical       REAL,
    avg_communication   REAL,
    avg_confidence       REAL,
    overall_score        REAL,
    strengths             TEXT,
    improvements          TEXT,
    summary               TEXT,
    generated_at          TEXT NOT NULL
);
```

---

## 4. Step-by-Step Setup Instructions

### Step 1 — Install Ollama
Download and install from **https://ollama.com** for your OS (Windows/Mac/Linux).

### Step 2 — Pull a model
Choose ONE (smaller models run faster on a laptop without a GPU):
```bash
ollama pull qwen2.5:3b
# or
ollama pull phi3
# or
ollama pull llama3.2
```

### Step 3 — Start the Ollama server
On most installs this runs automatically in the background. If not:
```bash
ollama serve
```

### Step 4 — Set up the Python project
```bash
cd ai-interview-coach
python -m venv venv

# Activate the virtual environment
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate            # Windows

pip install -r requirements.txt
```

### Step 5 — (Optional) Point the app at a specific model
By default the app uses `qwen2.5:3b` (set in `config.py`). To override without
editing code:
```bash
export OLLAMA_MODEL=phi3          # macOS/Linux
set OLLAMA_MODEL=phi3              # Windows
```

---

## 5. Run Commands

```bash
streamlit run app.py
```
This opens the app at **http://localhost:8501** in your browser.

**Usage flow:**
1. Enter the candidate's name in the sidebar.
2. (Optional) Uncheck any categories you want to skip.
3. Click **Start Interview**.
4. Type the candidate's answer in the chat box at the bottom for each question.
5. Review the live score chips + feedback after every answer.
6. Once all categories are done, click **Generate Final Report**.
7. Download the report as a Markdown file if needed.

---

## 6. Expected Output (what you'll see)

- **Sidebar:** App title, model name in use, candidate name field, category checklist, Start/Reset buttons, and a progress bar (`Category 3 of 11`).
- **Chat area:** Alternating assistant question bubbles (tagged with a colored category pill, e.g. `Python`) and candidate answer bubbles, each followed by three colored score chips (🟢/🟡/🔴 Technical / Communication / Confidence) and a highlighted feedback box.
- **Final report screen:** Four big score metrics at the top (Overall, Technical, Communication, Confidence), a bar chart of technical score by category, a text panel with STRENGTHS / AREAS TO IMPROVE / VERDICT, an expandable full transcript, and a "Download Report" button.

---

## 7. Future Enhancements

- 🎙️ **Voice integration** — the UI's chat input is already structured so a transcribed voice answer (e.g. via `streamlit-webrtc` or `st.audio_input` + Whisper) can be passed into `engine.submit_answer()` with zero changes to backend logic. Text-to-speech (e.g. Coqui TTS / pyttsx3) could read questions aloud.
- 📊 **Admin/analytics dashboard** — aggregate stats across all candidates using `database.get_all_sessions()`, which already exists but isn't yet surfaced in the UI.
- 🧠 **Adaptive difficulty** — adjust question difficulty per-category based on a rolling average instead of a fixed 3-question ramp.
- 🗂️ **Resume-based question generation** — parse an uploaded resume/project description and generate project-based questions tailored to it.
- 🔐 **Multi-user auth** — add login so each MCA student has a private history.
- 📄 **PDF report export** — extend `report_generator.py` to render a formatted PDF (e.g. via `reportlab`) alongside the existing Markdown export.
- 🌐 **Deployment** — containerize with Docker (Ollama + Streamlit) for lab-wide deployment on a college server.

---

## 8. Viva Questions & Answers (for project defense)

**Q1. Why did you choose Ollama instead of a cloud API like OpenAI?**
A: Ollama runs open-source LLMs (Phi-3, Qwen 2.5, Llama 3.2) entirely locally. This means zero API cost, no internet dependency during interviews, and full data privacy for student answers — important since this is meant for repeated student use in a lab setting.

**Q2. Why is the project split into `backend/`, `prompts/`, and `utils/` instead of one big file?**
A: This follows separation of concerns / clean architecture. The UI (`app.py`) never touches SQL or LLM calls directly — it only calls `InterviewEngine`. This makes each piece independently testable and replaceable (e.g., swapping Ollama for a cloud API only requires changing `llm_client.py`).

**Q3. How do you ensure the LLM's score isn't just made up or invalid?**
A: Two safeguards: (1) `utils/helpers.extract_json()` robustly parses JSON even if the model adds markdown fences or stray text; (2) `clamp_score()` forces every score into the valid 0–10 range, and `evaluator.py` applies deterministic rules (e.g., an empty answer always scores 0, a technical score below the threshold always forces a follow-up) so the LLM's judgement is never blindly trusted for edge cases.

**Q4. What happens if Ollama is not running or crashes mid-interview?**
A: `interview_engine.py` wraps every LLM call in a `try/except` and falls back to `question_bank.py`'s static, pre-written questions, so the interview can continue uninterrupted instead of crashing.

**Q5. How is the final score calculated?**
A: `evaluator.overall_score()` computes a weighted average: 60% technical, 25% communication, 15% confidence — reflecting that technical correctness should dominate a placement evaluation while still rewarding clear, confident articulation.

**Q6. Why SQLite instead of MySQL/PostgreSQL?**
A: SQLite is file-based and needs no separate server process, which is ideal for a single-machine academic project. The schema (`sessions`, `qa_log`, `reports`) is still fully relational and could be migrated to PostgreSQL later by only changing the connection logic in `database.py`.

**Q7. How does the follow-up question mechanism work?**
A: After scoring an answer, if `technical_score` is below `FOLLOW_UP_SCORE_THRESHOLD` (configurable in `config.py`) and the follow-up limit per question hasn't been used, `interview_engine._decide_next_action()` returns `"follow_up"`, and `generate_follow_up()` asks the LLM for one targeted question probing the specific weak answer.

