"""
app.py
------
Streamlit frontend for the AI Interview Coach. This file is intentionally
"dumb" — it only handles UI rendering and session_state wiring. All actual
interview logic lives in backend/interview_engine.py, which is the single
point of contact between this UI and the rest of the system.

Run with:
    streamlit run app.py
"""

import streamlit as st

from config import APP_TITLE, APP_ICON, QUESTION_CATEGORIES, OLLAMA_MODEL
from backend.database import init_db
from backend.interview_engine import InterviewEngine
from backend.report_generator import generate_report, report_to_markdown
from utils.helpers import score_badge

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
init_db()  # safe to call every run; creates tables only if missing

# A little custom CSS for a cleaner, more "modern chat app" feel than the
# Streamlit default — chat bubbles, score chips, and a tidier sidebar.
st.markdown(
    """
    <style>
        .score-chip {
            display: inline-block;
            padding: 2px 10px;
            margin-right: 6px;
            border-radius: 999px;
            font-size: 0.85rem;
            background-color: #f0f2f6;
            border: 1px solid #d8dee9;
        }
        .feedback-box {
            background-color: #f7f9fc;
            border-left: 4px solid #6c8ef5;
            padding: 10px 14px;
            border-radius: 6px;
            margin-top: 6px;
            font-size: 0.92rem;
        }
        .category-pill {
            background-color: #eef1ff;
            color: #3949ab;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Session state initialization
# --------------------------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state.engine = None          # InterviewEngine instance
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []          # list of dicts for chat rendering
if "awaiting_answer" not in st.session_state:
    st.session_state.awaiting_answer = False
if "report" not in st.session_state:
    st.session_state.report = None


def reset_session():
    """Clear all interview state so a new candidate can start fresh."""
    st.session_state.engine = None
    st.session_state.chat_log = []
    st.session_state.awaiting_answer = False
    st.session_state.report = None


# --------------------------------------------------------------------------
# Sidebar — candidate setup & controls
# --------------------------------------------------------------------------
with st.sidebar:
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.caption(f"Powered by local LLM via Ollama — current model: `{OLLAMA_MODEL}`")
    st.divider()

    student_name = st.text_input("Candidate Name", placeholder="e.g. Priya Sharma")

    selected_categories = st.multiselect(
        "Categories to cover",
        options=QUESTION_CATEGORIES,
        default=QUESTION_CATEGORIES,
        help="Uncheck any topic you'd like to skip in this mock interview.",
    )

    start_disabled = st.session_state.engine is not None or not student_name.strip()
    if st.button("🚀 Start Interview", disabled=start_disabled, use_container_width=True):
        engine = InterviewEngine(student_name.strip(), categories=selected_categories or QUESTION_CATEGORIES)
        engine.start()
        st.session_state.engine = engine
        st.session_state.chat_log = []
        st.session_state.report = None
        # Ask the very first question immediately.
        question = engine.get_next_question()
        st.session_state.chat_log.append(
            {"role": "assistant", "category": engine.current_category, "text": question}
        )
        st.session_state.awaiting_answer = True
        st.rerun()

    st.divider()
    if st.session_state.engine is not None and not st.session_state.engine.finished:
        completed, total = st.session_state.engine.progress()
        st.progress(completed / total if total else 0, text=f"Category {min(completed + 1, total)} of {total}")

    if st.button("🔄 Reset / New Candidate", use_container_width=True):
        reset_session()
        st.rerun()

    st.divider()
    st.caption(
        "🎙️ Voice input/output is planned as a future enhancement — "
        "see README for details. The text box below already mirrors how "
        "a transcribed voice answer would be submitted."
    )

# --------------------------------------------------------------------------
# Main area — chat interview UI
# --------------------------------------------------------------------------
st.header("💬 Mock Interview")

if st.session_state.engine is None:
    st.info("👈 Enter the candidate's name in the sidebar and click **Start Interview** to begin.")
else:
    engine: InterviewEngine = st.session_state.engine

    # Render the full chat history so far.
    for turn in st.session_state.chat_log:
        with st.chat_message("assistant" if turn["role"] == "assistant" else "user"):
            if turn["role"] == "assistant":
                st.markdown(f'<span class="category-pill">{turn["category"]}</span>', unsafe_allow_html=True)
                st.write(turn["text"])
            else:
                st.write(turn["text"])
                if "scores" in turn:
                    s = turn["scores"]
                    st.markdown(
                        f'<span class="score-chip">{score_badge(s["technical_score"])} '
                        f'Technical: {s["technical_score"]}/10</span>'
                        f'<span class="score-chip">{score_badge(s["communication_score"])} '
                        f'Communication: {s["communication_score"]}/10</span>'
                        f'<span class="score-chip">{score_badge(s["confidence_score"])} '
                        f'Confidence: {s["confidence_score"]}/10</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f'<div class="feedback-box">💡 {s["feedback"]}</div>', unsafe_allow_html=True)

    # Interview finished -> show the "generate report" call to action.
    if engine.finished:
        st.success("🎉 Interview complete! Generate the final report below.")
        if st.session_state.report is None:
            if st.button("📊 Generate Final Report", type="primary"):
                with st.spinner("Analyzing the full transcript and scoring performance..."):
                    st.session_state.report = generate_report(engine.session_id)
                st.rerun()

    # Answer input box (only while the interview is still active).
    elif st.session_state.awaiting_answer:
        answer = st.chat_input("Type the candidate's answer here...")
        if answer:
            with st.spinner("Evaluating answer..."):
                result = engine.submit_answer(answer)

            st.session_state.chat_log.append({"role": "user", "text": answer, "scores": result})

            next_action = result["next_action"]
            if next_action == "follow_up":
                follow_up_q = engine.get_follow_up_question()
                st.session_state.chat_log.append(
                    {"role": "assistant", "category": f"{engine.current_category} (follow-up)", "text": follow_up_q}
                )
            elif next_action == "next_question":
                next_q = engine.get_next_question()
                if next_q:
                    st.session_state.chat_log.append(
                        {"role": "assistant", "category": engine.current_category, "text": next_q}
                    )
                else:
                    engine.finished = True
                    engine.finish()
            elif next_action == "finished":
                engine.finish()

            st.rerun()

# --------------------------------------------------------------------------
# Final report rendering
# --------------------------------------------------------------------------
if st.session_state.report is not None:
    st.divider()
    st.header("📄 Final Interview Report")

    report = st.session_state.report
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Score", f"{report['overall_score']}/10")
    c2.metric("Avg Technical", f"{report['avg_technical']}/10")
    c3.metric("Avg Communication", f"{report['avg_communication']}/10")
    c4.metric("Avg Confidence", f"{report['avg_confidence']}/10")

    if report["category_breakdown"]:
        st.subheader("Category-wise Performance")
        chart_data = {
            cat: scores["technical"] for cat, scores in report["category_breakdown"].items()
        }
        st.bar_chart(chart_data)

    st.subheader("Examiner's Summary")
    st.text(report["summary_text"])

    with st.expander("📜 Full Transcript"):
        for row in report["qa_rows"]:
            tag = " · follow-up" if row["is_follow_up"] else ""
            st.markdown(f"**[{row['category']}{tag}]** {row['question']}")
            st.write(f"_Answer:_ {row['answer']}")
            st.caption(
                f"Technical {row['technical_score']}/10 · "
                f"Communication {row['communication_score']}/10 · "
                f"Confidence {row['confidence_score']}/10"
            )
            st.markdown("---")

    md_report = report_to_markdown(st.session_state.engine.student_name, report)
    st.download_button(
        "⬇️ Download Report (Markdown)",
        data=md_report,
        file_name=f"interview_report_{st.session_state.engine.session_id}.md",
        mime="text/markdown",
    )
