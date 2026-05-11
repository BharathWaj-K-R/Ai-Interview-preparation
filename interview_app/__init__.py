from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def create_app() -> "Flask":
    from flask import Flask
    from .db import close_db, init_db

    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
        static_url_path="/static",
    )
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key-change-in-production",
        DATABASE=Path(app.instance_path) / "interview.sqlite3",
    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_db(app)
    app.teardown_appcontext(close_db)

    from .routes import bp
    app.register_blueprint(bp)

    return app
