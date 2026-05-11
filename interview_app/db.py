import sqlite3
from pathlib import Path
from typing import Any

from flask import current_app, g


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_name TEXT NOT NULL,
    resume_text TEXT,
    round_type TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    overall_score REAL DEFAULT 0,
    confidence_score REAL DEFAULT 0,
    sentiment_score REAL DEFAULT 0,
    typing_score REAL DEFAULT 0,
    feedback TEXT
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_topic TEXT NOT NULL,
    round_type TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    typing_speed_wpm REAL DEFAULT 0,
    sentiment_score REAL DEFAULT 0,
    confidence_score REAL DEFAULT 0,
    relevance_score REAL DEFAULT 0,
    final_score REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""


FALLBACK_MEMORY_URI = "file:interview-prep-fallback?mode=memory&cache=shared"
_memory_keeper: sqlite3.Connection | None = None


def _build_connection(
    target: str,
    *,
    uri: bool = False,
    check_same_thread: bool = True,
) -> sqlite3.Connection:
    connection = sqlite3.connect(
        target,
        uri=uri,
        check_same_thread=check_same_thread,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def _fallback_memory_connection() -> sqlite3.Connection:
    global _memory_keeper

    if _memory_keeper is None:
        # Keep one connection open for app lifetime so shared in-memory DB persists.
        _memory_keeper = _build_connection(
            FALLBACK_MEMORY_URI,
            uri=True,
            check_same_thread=False,
        )
        _memory_keeper.executescript(SCHEMA_SQL)
        _memory_keeper.commit()

    return _memory_keeper


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE"])
        connection: sqlite3.Connection
        db_mode = "file"
        try:
            connection = _build_connection(str(database_path))
            connection.execute("PRAGMA journal_mode = MEMORY;")
            connection.execute("PRAGMA synchronous = NORMAL;")
            # Write probe catches filesystems where SQLite file locks/journals fail.
            connection.execute("CREATE TABLE IF NOT EXISTS _db_probe (id INTEGER PRIMARY KEY)")
            connection.commit()
        except sqlite3.OperationalError:
            connection = _fallback_memory_connection()
            db_mode = "memory"

        if db_mode == "file":
            try:
                connection.executescript(SCHEMA_SQL)
                connection.commit()
            except sqlite3.OperationalError:
                connection.close()
                connection = _fallback_memory_connection()
                db_mode = "memory"

        g.db_mode = db_mode
        g.db = connection
    return g.db


def close_db(_error: Exception | None = None) -> None:
    db: sqlite3.Connection | None = g.pop("db", None)
    db_mode = g.pop("db_mode", None)
    if db is not None and db_mode != "memory":
        db.close()


def init_db(app: Any) -> None:
    with app.app_context():
        db = get_db()
        try:
            db.executescript(SCHEMA_SQL)
            db.commit()
        except sqlite3.OperationalError:
            # Fallback for environments where filesystem locking blocks SQLite writes.
            if g.pop("db_mode", None) == "file":
                db.close()
            g.db = _fallback_memory_connection()
            g.db_mode = "memory"
            g.db.executescript(SCHEMA_SQL)
            g.db.commit()
