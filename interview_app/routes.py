from statistics import mean
from typing import Any, Dict, List

from flask import Blueprint, redirect, render_template, request, session, url_for

from .db import get_db
from .services.question_engine import generate_questions
from .services.recommendations import strengths_from_responses, weak_topics_from_responses
from .services.scoring import evaluate_response

bp = Blueprint("main", __name__)


def _questions_key(session_id: int) -> str:
    return f"interview_questions_{session_id}"


def _load_questions(session_id: int) -> List[Dict[str, Any]]:
    return session.get(_questions_key(session_id), [])


def _store_questions(session_id: int, questions: List[Dict[str, Any]]) -> None:
    session[_questions_key(session_id)] = questions


def _cleanup_questions(session_id: int) -> None:
    session.pop(_questions_key(session_id), None)


@bp.get("/")
def home():
    return render_template("index.html")


@bp.post("/start")
def start_interview():
    candidate_name = request.form.get("candidate_name", "").strip() or "Candidate"
    round_type = request.form.get("round_type", "both").strip().lower()
    resume_text = request.form.get("resume_text", "").strip()
    skills_text = request.form.get("skills_text", "").strip()
    profile_text = resume_text
    if skills_text:
        profile_text = f"{resume_text}\n\nSkills: {skills_text}".strip()

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO sessions (candidate_name, resume_text, round_type)
        VALUES (?, ?, ?)
        """,
        (candidate_name, profile_text, round_type),
    )
    db.commit()
    session_id = cursor.lastrowid

    questions = generate_questions(
        round_type=round_type,
        resume_text=resume_text,
        skills_text=skills_text,
        count=5,
    )
    _store_questions(session_id, questions)

    return redirect(url_for("main.interview_question", session_id=session_id, q_index=0))


@bp.get("/interview/<int:session_id>/<int:q_index>")
def interview_question(session_id: int, q_index: int):
    db = get_db()
    session_row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    questions = _load_questions(session_id)

    if session_row is None or not questions:
        return redirect(url_for("main.home"))

    if q_index >= len(questions):
        return redirect(url_for("main.dashboard", session_id=session_id))

    question = questions[q_index]
    return render_template(
        "interview.html",
        session_row=session_row,
        session_id=session_id,
        question=question,
        q_index=q_index,
        total_questions=len(questions),
    )


@bp.post("/submit/<int:session_id>/<int:q_index>")
def submit_answer(session_id: int, q_index: int):
    questions = _load_questions(session_id)
    if not questions or q_index >= len(questions):
        return redirect(url_for("main.home"))

    current_question = questions[q_index]
    answer_text = request.form.get("answer_text", "").strip()
    typing_wpm = float(request.form.get("typing_wpm", "0") or 0)

    if not answer_text:
        return redirect(url_for("main.interview_question", session_id=session_id, q_index=q_index))

    metrics = evaluate_response(
        question=current_question["text"],
        answer=answer_text,
        typing_wpm=typing_wpm,
        round_type=current_question["round_type"],
    )

    db = get_db()
    db.execute(
        """
        INSERT INTO responses (
            session_id,
            question_text,
            question_topic,
            round_type,
            answer_text,
            typing_speed_wpm,
            sentiment_score,
            confidence_score,
            relevance_score,
            final_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            current_question["text"],
            current_question["topic"],
            current_question["round_type"],
            answer_text,
            typing_wpm,
            metrics["sentiment_score"],
            metrics["confidence_score"],
            metrics["relevance_score"],
            metrics["final_score"],
        ),
    )
    db.commit()

    next_index = q_index + 1
    if next_index >= len(questions):
        _finalize_session_scores(session_id)
        _cleanup_questions(session_id)
        return redirect(url_for("main.dashboard", session_id=session_id))

    return redirect(url_for("main.interview_question", session_id=session_id, q_index=next_index))


def _finalize_session_scores(session_id: int) -> None:
    db = get_db()
    rows = db.execute("SELECT * FROM responses WHERE session_id = ?", (session_id,)).fetchall()
    if not rows:
        return

    overall = mean(float(row["final_score"]) for row in rows)
    confidence = mean(float(row["confidence_score"]) for row in rows)
    sentiment = mean(float(row["sentiment_score"]) for row in rows)
    typing = mean(float(row["typing_speed_wpm"]) for row in rows)

    weak_topics = weak_topics_from_responses(rows)
    strengths = strengths_from_responses(rows)

    feedback_parts: List[str] = []
    if strengths:
        feedback_parts.append("Strengths: " + " ".join(strengths))
    if weak_topics:
        topic_list = ", ".join(item["topic"] for item in weak_topics)
        feedback_parts.append(f"Focus next on: {topic_list}.")
    else:
        feedback_parts.append("Balanced performance across topics. Keep momentum.")

    final_feedback = " ".join(feedback_parts)
    db.execute(
        """
        UPDATE sessions
        SET overall_score = ?, confidence_score = ?, sentiment_score = ?, typing_score = ?, feedback = ?
        WHERE id = ?
        """,
        (
            round(overall, 2),
            round(confidence, 2),
            round(sentiment, 2),
            round(typing, 2),
            final_feedback,
            session_id,
        ),
    )
    db.commit()


@bp.get("/dashboard/<int:session_id>")
def dashboard(session_id: int):
    db = get_db()
    session_row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    responses = db.execute(
        "SELECT * FROM responses WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()

    if session_row is None:
        return redirect(url_for("main.home"))

    weak_topics = weak_topics_from_responses(responses)
    strengths = strengths_from_responses(responses)

    return render_template(
        "dashboard.html",
        session_row=session_row,
        responses=responses,
        weak_topics=weak_topics,
        strengths=strengths,
    )
