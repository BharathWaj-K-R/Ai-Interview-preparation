from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def user_or_ip_key() -> str:
    try:
        from flask_login import current_user

        if current_user.is_authenticated:
            return f"user:{current_user.get_id()}"
    except RuntimeError:
        pass
    return get_remote_address()


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=user_or_ip_key)
