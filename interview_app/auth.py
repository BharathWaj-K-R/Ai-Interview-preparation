from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import User

def get_user_by_id(user_id: str | int) -> User | None:
    return db.session.get(User, int(user_id))


def get_user_by_email(email: str) -> User | None:
    return User.query.filter(db.func.lower(User.email) == email.strip().lower()).first()


def create_user(email: str, password: str) -> User:
    user = User(email=email.strip().lower(), password_hash=generate_password_hash(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("An account with this email already exists.") from exc
    return user
