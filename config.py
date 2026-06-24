"""
config.py
---------
Centralized configuration for the AI Interview Coach application.
Keeping all tunable values in one place makes the app easy to
re-configure without touching business logic.
"""

import os

# --------------------------------------------------------------------------
# Ollama / LLM Configuration
# --------------------------------------------------------------------------
# You can switch models freely. Any locally-pulled Ollama model works:
#   ollama pull qwen2.5:3b
#   ollama pull phi3
#   ollama pull llama3.2
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_TEMPERATURE = 0.4          # Lower = more consistent/predictable scoring
LLM_REQUEST_TIMEOUT = 120      # seconds, generous for slower local hardware

# --------------------------------------------------------------------------
# Database Configuration
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "interview_history.db")

# --------------------------------------------------------------------------
# Interview Configuration
# --------------------------------------------------------------------------
# Order in which categories are presented to the candidate.
QUESTION_CATEGORIES = [
    "Python",
    "Java",
    "Data Structures",
    "DBMS",
    "SQL",
    "Operating Systems",
    "Computer Networks",
    "Machine Learning",
    "Generative AI",
    "Project-Based",
    "HR",
]

QUESTIONS_PER_CATEGORY = 2          # Base (non-follow-up) questions per category
MAX_FOLLOW_UPS_PER_QUESTION = 1     # Cap follow-ups so interviews stay focused
FOLLOW_UP_SCORE_THRESHOLD = 6       # If technical_score < this, a follow-up is asked

# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
SCORE_MIN, SCORE_MAX = 0, 10

# --------------------------------------------------------------------------
# App Metadata
# --------------------------------------------------------------------------
APP_TITLE = "AI Interview Coach for MCA Students"
APP_ICON = "🎓"
