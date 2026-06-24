"""
backend/interview_engine.py
-----------------------------
The InterviewEngine is the single orchestrator of an interview session.
The Streamlit frontend should only ever talk to THIS class — it should
never call database.py or llm_client.py directly. That separation is
what keeps frontend and backend cleanly decoupled.

Typical usage (mirrors what app.py does):

    engine = InterviewEngine(student_name="Asha")
    engine.start()
    question = engine.get_next_question()
    result = engine.submit_answer(question, "my answer text")
    ...
    engine.finish()
"""

from config import (
    QUESTION_CATEGORIES,
    QUESTIONS_PER_CATEGORY,
    MAX_FOLLOW_UPS_PER_QUESTION,
)
from backend import database, evaluator, llm_client
from backend.question_bank import get_fallback_question
from utils.helpers import new_session_id


class InterviewEngine:
    """Drives one end-to-end mock interview session for a single candidate."""

    def __init__(self, student_name: str, categories: list[str] | None = None):
        self.student_name = student_name
        self.categories = categories or QUESTION_CATEGORIES
        self.session_id = new_session_id()

        # Internal progress trackers
        self._category_index = 0
        self._questions_asked_in_category = 0
        self._follow_ups_used_for_current_question = 0
        self._asked_questions_by_category: dict[str, list[str]] = {c: [] for c in self.categories}

        self.current_question: str | None = None
        self.current_category: str | None = None
        self.is_follow_up_question: bool = False
        self.finished: bool = False

    # ----------------------------------------------------------------------
    # Session lifecycle
    # ----------------------------------------------------------------------
    def start(self) -> None:
        """Persist a new session row and prepare the first question."""
        database.create_session(self.session_id, self.student_name)

    def finish(self) -> None:
        """Mark the session as completed in the database."""
        database.end_session(self.session_id)
        self.finished = True

    # ----------------------------------------------------------------------
    # Question flow
    # ----------------------------------------------------------------------
    def _current_category_name(self) -> str | None:
        if self._category_index >= len(self.categories):
            return None
        return self.categories[self._category_index]

    def get_next_question(self) -> str | None:
        """
        Return the next question to ask, advancing through categories in
        order. Returns None once every category is exhausted (interview over).
        """
        category = self._current_category_name()
        if category is None:
            self.finished = True
            return None

        self.current_category = category
        self.is_follow_up_question = False

        try:
            question = llm_client.generate_question(
                category=category,
                difficulty=self._difficulty_for_progress(),
                previous_questions=self._asked_questions_by_category[category],
            )
            if not question:
                raise ValueError("Empty question returned by LLM")
        except Exception:
            # LLM unreachable / malformed output -> use the static fallback bank.
            question = get_fallback_question(category, self._asked_questions_by_category[category])

        self._asked_questions_by_category[category].append(question)
        self.current_question = question
        return question

    def _difficulty_for_progress(self) -> str:
        """Simple ramp: start easy, get harder as the candidate progresses."""
        if self._questions_asked_in_category == 0:
            return "easy"
        if self._questions_asked_in_category == 1:
            return "medium"
        return "hard"

    def submit_answer(self, answer: str) -> dict:
        """
        Evaluate the candidate's answer to self.current_question, log it,
        and decide what happens next (follow-up vs. move on).

        Returns the evaluation dict plus a "next_action" hint for the UI:
            "follow_up"     -> call get_follow_up_question() next
            "next_question" -> call get_next_question() next
            "finished"      -> interview is complete
        """
        if self.current_question is None or self.current_category is None:
            raise RuntimeError("submit_answer() called before a question was asked.")

        result = evaluator.evaluate(self.current_category, self.current_question, answer)

        database.log_qa(
            session_id=self.session_id,
            category=self.current_category,
            question=self.current_question,
            answer=answer,
            technical_score=result["technical_score"],
            communication_score=result["communication_score"],
            confidence_score=result["confidence_score"],
            feedback=result["feedback"],
            is_follow_up=self.is_follow_up_question,
        )

        next_action = self._decide_next_action(result)
        result["next_action"] = next_action
        return result

    def _decide_next_action(self, result: dict) -> str:
        """Pure decision logic, kept separate from I/O for easy unit testing."""
        can_follow_up = (
            result["needs_follow_up"]
            and not self.is_follow_up_question
            and self._follow_ups_used_for_current_question < MAX_FOLLOW_UPS_PER_QUESTION
        )

        if can_follow_up:
            return "follow_up"

        # Move on: either to the next base question in this category, or
        # to the next category entirely.
        self._questions_asked_in_category += 1
        self._follow_ups_used_for_current_question = 0

        if self._questions_asked_in_category >= QUESTIONS_PER_CATEGORY:
            self._questions_asked_in_category = 0
            self._category_index += 1

        if self._category_index >= len(self.categories):
            return "finished"
        return "next_question"

    def get_follow_up_question(self) -> str:
        """Generate and return a follow-up question for the previous weak answer."""
        try:
            follow_up = llm_client.generate_follow_up(
                question=self.current_question,
                answer="(see previous answer)",
                technical_score=0,
            )
            if not follow_up:
                raise ValueError("Empty follow-up returned by LLM")
        except Exception:
            follow_up = f"Can you elaborate further or give a concrete example for: '{self.current_question}'?"

        self._follow_ups_used_for_current_question += 1
        self.is_follow_up_question = True
        self.current_question = follow_up
        return follow_up

    # ----------------------------------------------------------------------
    # Progress info (for the Streamlit progress bar)
    # ----------------------------------------------------------------------
    def progress(self) -> tuple[int, int]:
        """Return (categories_completed, total_categories) for a progress bar."""
        return self._category_index, len(self.categories)
