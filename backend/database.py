"""
backend/database.py
--------------------
All SQLite persistence logic lives here. No other module should open a
raw sqlite3 connection — they call into these functions instead. This
keeps the schema and SQL in exactly one place (clean architecture /
single responsibility).

Schema
------
sessions   : one row per interview session
qa_log     : one row per question asked (and its evaluation)
reports    : one row per generated final report (1:1 with a session)
"""

import sqlite3
from contextlib import contextmanager

from config import DB_PATH, DATA_DIR
import os
from utils.helpers import now_iso

# Ensure the data directory exists before any connection is attempted.
os.makedirs(DATA_DIR, exist_ok=True)


@contextmanager
def get_connection():
    """
    Context manager that yields a SQLite connection and guarantees it is
    committed and closed even if an exception occurs mid-transaction.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts (row["col"])
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they do not already exist. Safe to call on every app start."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                student_name TEXT NOT NULL,
                started_at   TEXT NOT NULL,
                ended_at     TEXT,
                status       TEXT NOT NULL DEFAULT 'in_progress'
            );

            CREATE TABLE IF NOT EXISTS qa_log (
                qa_id               INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id          TEXT NOT NULL,
                category            TEXT NOT NULL,
                question            TEXT NOT NULL,
                answer              TEXT NOT NULL,
                technical_score     INTEGER,
                communication_score INTEGER,
                confidence_score    INTEGER,
                feedback            TEXT,
                is_follow_up        INTEGER NOT NULL DEFAULT 0,
                created_at          TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            );

            CREATE TABLE IF NOT EXISTS reports (
                report_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id       TEXT NOT NULL,
                avg_technical     REAL,
                avg_communication REAL,
                avg_confidence     REAL,
                overall_score      REAL,
                strengths          TEXT,
                improvements       TEXT,
                summary            TEXT,
                generated_at       TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            );
            """
        )


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------
def create_session(session_id: str, student_name: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, student_name, started_at, status) "
            "VALUES (?, ?, ?, 'in_progress')",
            (session_id, student_name, now_iso()),
        )


def end_session(session_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = ?, status = 'completed' WHERE session_id = ?",
            (now_iso(), session_id),
        )


def get_all_sessions() -> list:
    """Return every session, most recent first (used for a history/admin view)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Q&A Log
# --------------------------------------------------------------------------
def log_qa(
    session_id: str,
    category: str,
    question: str,
    answer: str,
    technical_score: int,
    communication_score: int,
    confidence_score: int,
    feedback: str,
    is_follow_up: bool = False,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO qa_log (
                session_id, category, question, answer,
                technical_score, communication_score, confidence_score,
                feedback, is_follow_up, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, category, question, answer,
                technical_score, communication_score, confidence_score,
                feedback, int(is_follow_up), now_iso(),
            ),
        )


def get_qa_for_session(session_id: str) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM qa_log WHERE session_id = ? ORDER BY qa_id ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------
def save_report(
    session_id: str,
    avg_technical: float,
    avg_communication: float,
    avg_confidence: float,
    overall_score: float,
    strengths: str,
    improvements: str,
    summary: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reports (
                session_id, avg_technical, avg_communication, avg_confidence,
                overall_score, strengths, improvements, summary, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, avg_technical, avg_communication, avg_confidence,
                overall_score, strengths, improvements, summary, now_iso(),
            ),
        )


def get_report(session_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE session_id = ? ORDER BY report_id DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
