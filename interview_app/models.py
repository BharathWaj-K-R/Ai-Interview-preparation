from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash

from .extensions import db


class AttrDictMixin:
    def __getitem__(self, key: str):
        return getattr(self, key)


class User(UserMixin, AttrDictMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sessions = db.relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")

    def get_id(self) -> str:
        return str(self.id)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class InterviewSession(AttrDictMixin, db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_name = db.Column(db.String(255), nullable=False)
    resume_text = db.Column(db.Text)
    round_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    overall_score = db.Column(db.Float, default=0)
    confidence_score = db.Column(db.Float, default=0)
    sentiment_score = db.Column(db.Float, default=0)
    typing_score = db.Column(db.Float, default=0)
    feedback = db.Column(db.Text)

    user = db.relationship("User", back_populates="sessions")
    responses = db.relationship("Response", back_populates="session", cascade="all, delete-orphan")


class Response(AttrDictMixin, db.Model):
    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    question_topic = db.Column(db.String(255), nullable=False)
    round_type = db.Column(db.String(50), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    typing_speed_wpm = db.Column(db.Float, default=0)
    sentiment_score = db.Column(db.Float, default=0)
    confidence_score = db.Column(db.Float, default=0)
    relevance_score = db.Column(db.Float, default=0)
    final_score = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    session = db.relationship("InterviewSession", back_populates="responses")
