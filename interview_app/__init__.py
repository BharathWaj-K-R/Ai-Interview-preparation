from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def create_app(config_overrides: dict | None = None) -> "Flask":
    from flask import Flask
    from .extensions import db, limiter, login_manager, migrate
    from .auth import get_user_by_id
    from config import Config

    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
        static_url_path="/static",
    )
    app.config.from_object(Config)
    if config_overrides:
        if "DATABASE" in config_overrides and "SQLALCHEMY_DATABASE_URI" not in config_overrides:
            database_path = Path(config_overrides["DATABASE"]).resolve()
            database_path.parent.mkdir(parents=True, exist_ok=True)
            config_overrides = {
                **config_overrides,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
            }
        app.config.update(config_overrides)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    login_manager.login_view = "main.login"
    login_manager.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return get_user_by_id(user_id)

    from . import models  # noqa: F401
    if app.config.get("TESTING") or app.config.get("AUTO_CREATE_DB"):
        with app.app_context():
            db.create_all()

    from .routes import bp
    app.register_blueprint(bp)

    return app
