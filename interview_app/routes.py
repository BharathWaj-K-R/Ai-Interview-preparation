from statistics import mean
from typing import Any, Dict, List

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from flask_login import current_user, login_required, login_user, logout_user

from .auth import create_user, get_user_by_email
from .extensions import db, limiter
from .models import InterviewSession, Response
from .services.question_engine import generate_questions
from .services.resume_parser import parse_resume_file
from .services.recommendations import strengths_from_responses, weak_topics_from_responses
from .services.scoring import evaluate_answer

bp = Blueprint("main", __name__)


def _questions_key(session_id: int) -> str:
    return f"interview_questions_{session_id}"


def _load_questions(session_id: int) -> List[Dict[str, Any]]:
    return session.get(_questions_key(session_id), [])


def _store_questions(session_id: int, questions: List[Dict[str, Any]]) -> None:
    session[_questions_key(session_id)] = questions


def _cleanup_questions(session_id: int) -> None:
    session.pop(_questions_key(session_id), None)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("register.html")
        try:
            user = create_user(email, password)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("register.html")
        login_user(user)
        return redirect(url_for("main.home"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user is None or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        login_user(user)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("main.home"))

    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


def _session_row_or_403(session_id: int):
    row = db.session.get(InterviewSession, session_id)
    if row is None:
        return None
    if row.user_id != current_user.id:
        abort(403)
    return row


@bp.get("/")
@login_required
def home():
    return render_template("index.html")


@bp.post("/start")
@login_required
@limiter.limit("20/hour")
def start_interview():
    candidate_name = request.form.get("candidate_name", "").strip() or "Candidate"
    round_type = request.form.get("round_type", "both").strip().lower()
    pasted_resume_text = request.form.get("resume_text", "").strip()
    skills_text = request.form.get("skills_text", "").strip()
    uploaded_resume_text = ""
    resume_file = request.files.get("resume_file")
    if resume_file and resume_file.filename:
        try:
            uploaded_resume_text = parse_resume_file(resume_file.stream, resume_file.filename).strip()
        except Exception as exc:
            flash(f"Could not parse uploaded resume: {exc}", "error")

    resume_text = "\n\n".join(
        part for part in [pasted_resume_text, uploaded_resume_text] if part
    )
    profile_text = resume_text
    if skills_text:
        profile_text = f"{resume_text}\n\nSkills: {skills_text}".strip()

    interview_session = InterviewSession(
        user_id=current_user.id,
        candidate_name=candidate_name,
        resume_text=profile_text,
        round_type=round_type,
    )
    db.session.add(interview_session)
    db.session.commit()
    session_id = interview_session.id

    questions = generate_questions(
        round_type=round_type,
        resume_text=resume_text,
        skills_text=skills_text,
        count=int(current_app.config.get("MAX_QUESTIONS", 5)),
    )
    _store_questions(session_id, questions)

    return redirect(url_for("main.interview_question", session_id=session_id, q_index=0))


@bp.get("/interview/<int:session_id>/<int:q_index>")
@login_required
def interview_question(session_id: int, q_index: int):
    session_row = _session_row_or_403(session_id)
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
@login_required
@limiter.limit("20/hour")
def submit_answer(session_id: int, q_index: int):
    if _session_row_or_403(session_id) is None:
        return redirect(url_for("main.home"))
    questions = _load_questions(session_id)
    if not questions or q_index >= len(questions):
        return redirect(url_for("main.home"))

    current_question = questions[q_index]
    answer_text = request.form.get("answer_text", "").strip()
    typing_wpm = float(request.form.get("typing_wpm", "0") or 0)

    if not answer_text:
        return redirect(url_for("main.interview_question", session_id=session_id, q_index=q_index))

    metrics = evaluate_answer(
        question=current_question["text"],
        answer=answer_text,
        typing_wpm=typing_wpm,
        round_type=current_question["round_type"],
    )

    response = Response(
        session_id=session_id,
        question_text=current_question["text"],
        question_topic=current_question["topic"],
        round_type=current_question["round_type"],
        answer_text=answer_text,
        typing_speed_wpm=typing_wpm,
        sentiment_score=metrics["sentiment_score"],
        confidence_score=metrics["confidence_score"],
        relevance_score=metrics["relevance_score"],
        final_score=metrics["final_score"],
    )
    db.session.add(response)
    db.session.commit()

    next_index = q_index + 1
    if next_index >= len(questions):
        _finalize_session_scores(session_id)
        _cleanup_questions(session_id)
        return redirect(url_for("main.dashboard", session_id=session_id))

    return redirect(url_for("main.interview_question", session_id=session_id, q_index=next_index))


def _finalize_session_scores(session_id: int) -> None:
    rows = Response.query.filter_by(session_id=session_id).order_by(Response.id.asc()).all()
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
    interview_session = db.session.get(InterviewSession, session_id)
    if interview_session is None:
        return
    interview_session.overall_score = round(overall, 2)
    interview_session.confidence_score = round(confidence, 2)
    interview_session.sentiment_score = round(sentiment, 2)
    interview_session.typing_score = round(typing, 2)
    interview_session.feedback = final_feedback
    db.session.commit()


@bp.get("/dashboard/<int:session_id>")
@login_required
def dashboard(session_id: int):
    session_row = _session_row_or_403(session_id)
    responses = Response.query.filter_by(session_id=session_id).order_by(Response.id.asc()).all()

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
