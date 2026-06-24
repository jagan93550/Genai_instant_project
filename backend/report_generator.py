"""
backend/report_generator.py
------------------------------
Builds the final interview report once a session is complete:
- Pulls every Q&A row for the session from the database.
- Computes per-category and overall numeric averages.
- Asks the LLM to write a qualitative STRENGTHS / IMPROVE / VERDICT summary.
- Persists the report row so it can be re-displayed later without
  re-calling the LLM.
"""

from backend import database, llm_client, evaluator


def _build_transcript(qa_rows: list[dict]) -> str:
    """Turn raw DB rows into a readable transcript block for the LLM prompt."""
    lines = []
    for row in qa_rows:
        tag = " (follow-up)" if row["is_follow_up"] else ""
        lines.append(
            f"[{row['category']}]{tag}\n"
            f"Q: {row['question']}\n"
            f"A: {row['answer']}\n"
            f"Scores -> Technical: {row['technical_score']}/10, "
            f"Communication: {row['communication_score']}/10, "
            f"Confidence: {row['confidence_score']}/10\n"
        )
    return "\n".join(lines)


def _category_breakdown(qa_rows: list[dict]) -> dict[str, dict]:
    """Average scores per category, used for the bar chart in the UI."""
    by_category: dict[str, list[dict]] = {}
    for row in qa_rows:
        by_category.setdefault(row["category"], []).append(row)

    breakdown = {}
    for category, rows in by_category.items():
        n = len(rows)
        breakdown[category] = {
            "technical": round(sum(r["technical_score"] for r in rows) / n, 2),
            "communication": round(sum(r["communication_score"] for r in rows) / n, 2),
            "confidence": round(sum(r["confidence_score"] for r in rows) / n, 2),
        }
    return breakdown


def generate_report(session_id: str) -> dict:
    """
    Generate (or regenerate) the final report for a session.

    Returns a dict with: avg_technical, avg_communication, avg_confidence,
    overall_score, category_breakdown, summary_text (STRENGTHS/IMPROVE/VERDICT),
    and raw qa_rows (for a detailed transcript view in the UI).
    """
    qa_rows = database.get_qa_for_session(session_id)

    if not qa_rows:
        return {
            "avg_technical": 0, "avg_communication": 0, "avg_confidence": 0,
            "overall_score": 0, "category_breakdown": {}, "summary_text": "No answers recorded.",
            "qa_rows": [],
        }

    n = len(qa_rows)
    avg_technical = round(sum(r["technical_score"] for r in qa_rows) / n, 2)
    avg_communication = round(sum(r["communication_score"] for r in qa_rows) / n, 2)
    avg_confidence = round(sum(r["confidence_score"] for r in qa_rows) / n, 2)
    overall = evaluator.overall_score(avg_technical, avg_communication, avg_confidence)

    transcript = _build_transcript(qa_rows)
    try:
        summary_text = llm_client.generate_final_summary(transcript)
    except Exception:
        summary_text = (
            "STRENGTHS:\n- (Summary unavailable — LLM could not be reached)\n\n"
            "AREAS TO IMPROVE:\n- (Summary unavailable — LLM could not be reached)\n\n"
            "VERDICT:\nPlease ensure Ollama is running and retry generating the report."
        )

    # Very rough strengths/improvements split purely for DB storage; the
    # full text is stored as-is in `summary` and re-parsed by the UI for display.
    database.save_report(
        session_id=session_id,
        avg_technical=avg_technical,
        avg_communication=avg_communication,
        avg_confidence=avg_confidence,
        overall_score=overall,
        strengths="", improvements="",
        summary=summary_text,
    )

    return {
        "avg_technical": avg_technical,
        "avg_communication": avg_communication,
        "avg_confidence": avg_confidence,
        "overall_score": overall,
        "category_breakdown": _category_breakdown(qa_rows),
        "summary_text": summary_text,
        "qa_rows": qa_rows,
    }


def report_to_markdown(student_name: str, report: dict) -> str:
    """Render a report dict as a downloadable Markdown document."""
    lines = [
        f"# Interview Report — {student_name}",
        "",
        f"**Overall Score:** {report['overall_score']}/10",
        f"**Average Technical Score:** {report['avg_technical']}/10",
        f"**Average Communication Score:** {report['avg_communication']}/10",
        f"**Average Confidence Score:** {report['avg_confidence']}/10",
        "",
        "## Category Breakdown",
    ]
    for category, scores in report["category_breakdown"].items():
        lines.append(
            f"- **{category}** — Technical: {scores['technical']}/10, "
            f"Communication: {scores['communication']}/10, "
            f"Confidence: {scores['confidence']}/10"
        )

    lines += ["", "## Summary", "", report["summary_text"], "", "## Full Transcript", ""]
    for row in report["qa_rows"]:
        tag = " (follow-up)" if row["is_follow_up"] else ""
        lines.append(f"**[{row['category']}]{tag} Q:** {row['question']}")
        lines.append(f"**A:** {row['answer']}")
        lines.append(
            f"*Scores — Technical: {row['technical_score']}/10, "
            f"Communication: {row['communication_score']}/10, "
            f"Confidence: {row['confidence_score']}/10*"
        )
        lines.append(f"_Feedback: {row['feedback']}_")
        lines.append("")

    return "\n".join(lines)
