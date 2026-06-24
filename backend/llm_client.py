"""
backend/llm_client.py
----------------------
Thin wrapper around the local Ollama runtime. This is the ONLY module
that talks to the LLM — every other module calls functions defined here.
That isolation means swapping Ollama for another backend (e.g. a hosted
API) later only requires changes in this one file.

Requires a running local Ollama server:
    https://ollama.com  ->  `ollama serve`  (usually auto-started)
And at least one pulled model, e.g.:
    ollama pull qwen2.5:3b
"""

import ollama

from config import OLLAMA_MODEL, OLLAMA_HOST, LLM_TEMPERATURE
from prompts.system_prompt import (
    INTERVIEWER_SYSTEM_PROMPT,
    INTERVIEWER_QUESTION_TEMPLATE,
    INTERVIEWER_FOLLOWUP_TEMPLATE,
    EVALUATOR_SYSTEM_PROMPT,
    EVALUATOR_USER_TEMPLATE,
    REPORT_SUMMARY_SYSTEM_PROMPT,
    REPORT_SUMMARY_USER_TEMPLATE,
)
from utils.helpers import extract_json, clamp_score

# A single shared client pointed at the configured Ollama host.
_client = ollama.Client(host=OLLAMA_HOST)


def _chat(system_prompt: str, user_prompt: str) -> str:
    """
    Low-level helper: send a system + user message pair to Ollama and
    return the raw text response. All higher-level functions build on this.
    """
    try:
        response = _client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": LLM_TEMPERATURE},
        )
        return response["message"]["content"].strip()
    except Exception as exc:
        # Surface a clear, actionable error instead of a raw stack trace.
        raise RuntimeError(
            f"Could not reach Ollama model '{OLLAMA_MODEL}' at {OLLAMA_HOST}. "
            f"Is `ollama serve` running and has the model been pulled? "
            f"Original error: {exc}"
        ) from exc


def generate_question(category: str, difficulty: str, previous_questions: list[str]) -> str:
    """Ask the LLM for the next interview question in a given category."""
    prev = "\n".join(f"- {q}" for q in previous_questions) or "(none yet)"
    user_prompt = INTERVIEWER_QUESTION_TEMPLATE.format(
        category=category, difficulty=difficulty, previous_questions=prev
    )
    question = _chat(INTERVIEWER_SYSTEM_PROMPT, user_prompt)
    # Defensive cleanup: strip stray quotes/numbering the model sometimes adds.
    return question.strip().strip('"').lstrip("0123456789.- ")


def generate_follow_up(question: str, answer: str, technical_score: int) -> str:
    """Ask the LLM for a targeted follow-up question after a weak answer."""
    user_prompt = INTERVIEWER_FOLLOWUP_TEMPLATE.format(
        question=question, answer=answer, technical_score=technical_score
    )
    follow_up = _chat(INTERVIEWER_SYSTEM_PROMPT, user_prompt)
    return follow_up.strip().strip('"')


def evaluate_answer(category: str, question: str, answer: str) -> dict:
    """
    Ask the LLM to score a candidate's answer.

    Returns a dict with keys: technical_score, communication_score,
    confidence_score, feedback, needs_follow_up. Falls back to safe
    defaults if the model's output cannot be parsed, so the UI never
    crashes on a malformed LLM response.
    """
    user_prompt = EVALUATOR_USER_TEMPLATE.format(
        category=category, question=question, answer=answer
    )
    raw = _chat(EVALUATOR_SYSTEM_PROMPT, user_prompt)
    parsed = extract_json(raw)

    if not parsed:
        # Graceful fallback so a single bad LLM response never breaks the flow.
        return {
            "technical_score": 0,
            "communication_score": 0,
            "confidence_score": 0,
            "feedback": "Could not automatically evaluate this answer. "
                        "Please review it manually.",
            "needs_follow_up": False,
        }

    return {
        "technical_score": clamp_score(parsed.get("technical_score", 0)),
        "communication_score": clamp_score(parsed.get("communication_score", 0)),
        "confidence_score": clamp_score(parsed.get("confidence_score", 0)),
        "feedback": str(parsed.get("feedback", "")).strip(),
        "needs_follow_up": bool(parsed.get("needs_follow_up", False)),
    }


def generate_final_summary(transcript: str) -> str:
    """Ask the LLM to write the qualitative STRENGTHS / IMPROVE / VERDICT summary."""
    user_prompt = REPORT_SUMMARY_USER_TEMPLATE.format(transcript=transcript)
    return _chat(REPORT_SUMMARY_SYSTEM_PROMPT, user_prompt)
