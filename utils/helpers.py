"""
utils/helpers.py
-----------------
Small, generic helper functions used across the backend and frontend.
Keeping these separate avoids duplicating logic in multiple modules.
"""

import json
import re
import uuid
from datetime import datetime


def now_iso() -> str:
    """Return the current timestamp as an ISO-8601 string (used for DB rows)."""
    return datetime.now().isoformat(timespec="seconds")


def new_session_id() -> str:
    """Generate a short, unique session id for a new interview session."""
    return uuid.uuid4().hex[:12]


def clamp_score(value, low: int = 0, high: int = 10) -> int:
    """
    Force a numeric score into the valid [low, high] range.
    LLMs occasionally return out-of-range or malformed numbers, so every
    score must pass through this before being stored or displayed.
    """
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        return low
    return max(low, min(high, value))


def extract_json(text: str) -> dict:
    """
    Robustly extract a JSON object from an LLM's text response.

    Open-source LLMs (Phi-3 / Qwen / Llama) often wrap JSON in markdown
    fences or add a short preamble like "Here is the evaluation:".
    This function strips that noise and parses the first valid JSON
    object it can find. Returns {} if nothing parseable is found.
    """
    if not text:
        return {}

    # 1) Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"```(?:json)?", "", text).strip()

    # 2) Try a direct parse first (fast path for well-behaved models)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3) Fall back to locating the first {...} block via brace matching
    start = cleaned.find("{")
    if start == -1:
        return {}

    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return {}
    return {}


def score_badge(score: int) -> str:
    """Return a small emoji badge representing a 0-10 score, for UI display."""
    if score >= 8:
        return "🟢"
    if score >= 5:
        return "🟡"
    return "🔴"
