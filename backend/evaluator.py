"""
backend/evaluator.py
---------------------
Sits between the InterviewEngine and llm_client. Responsible for:
- Calling the LLM to score an answer.
- Applying deterministic safety nets (e.g. an empty answer always scores 0
  regardless of what the LLM says — never trust the LLM blindly for edge cases).
- Deciding whether a follow-up question is warranted, combining the LLM's
  own judgement with a hard rule based on the configured threshold.
"""

from backend import llm_client
from config import FOLLOW_UP_SCORE_THRESHOLD


def evaluate(category: str, question: str, answer: str) -> dict:
    """
    Evaluate a single candidate answer and return a normalized result:

    {
        "technical_score": int,
        "communication_score": int,
        "confidence_score": int,
        "feedback": str,
        "needs_follow_up": bool,
    }
    """
    answer_clean = (answer or "").strip()

    # Deterministic edge case: don't bother calling the LLM for an empty answer.
    if not answer_clean:
        return {
            "technical_score": 0,
            "communication_score": 0,
            "confidence_score": 0,
            "feedback": "No answer was provided. Try to attempt every question, "
                        "even partially — interviewers value effort and partial "
                        "reasoning over silence.",
            "needs_follow_up": False,
        }

    result = llm_client.evaluate_answer(category, question, answer_clean)

    # Hard rule layered on top of the LLM's own opinion: a sufficiently low
    # technical score always triggers a follow-up, regardless of what the
    # model decided, so weak understanding never silently slips through.
    if result["technical_score"] < FOLLOW_UP_SCORE_THRESHOLD:
        result["needs_follow_up"] = True

    return result


def overall_score(technical: float, communication: float, confidence: float) -> float:
    """
    Weighted overall score for a single answer or a session average.
    Technical understanding is weighted highest, as is standard for
    placement evaluations, with communication and confidence as
    supporting signals.
    """
    weighted = (technical * 0.6) + (communication * 0.25) + (confidence * 0.15)
    return round(weighted, 2)
