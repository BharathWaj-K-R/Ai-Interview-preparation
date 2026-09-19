# AI-Based Interview Preparation System

A production-ready Flask application for placement interview practice. Users register, upload or paste a resume, enter key skills, complete technical/HR mock interviews, and receive AI-backed scoring plus weak-topic recommendations.

## Features

- Anthropic LLM integration for resume and skills-based question generation
- LLM answer evaluation with heuristic fallback when no API key is configured
- PDF and DOCX resume parsing
- Flask-Login authentication with user-scoped interview sessions
- SQLAlchemy models with SQLite for development and PostgreSQL for production
- Alembic/Flask-Migrate database migrations
- Flask-Limiter protection on LLM-costly routes
- Docker and docker-compose deployment setup
- GitHub Actions CI running the unittest suite

## Architecture

```text
Browser
  -> Flask routes
      -> Auth layer (Flask-Login)
      -> Rate limiter (Flask-Limiter)
      -> Resume parser (pdfplumber / python-docx)
      -> Question engine
          -> Anthropic API
          -> Heuristic fallback
      -> Scoring engine
          -> Anthropic API
          -> Heuristic fallback
      -> SQLAlchemy models
          -> SQLite in dev
          -> PostgreSQL in prod
      -> Dashboard templates
```

## Local Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
flask db upgrade
python app.py
```

Open `http://127.0.0.1:5000`.

## Environment

Configure `.env` from `.env.example`.

```text
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:///instance/interview.sqlite3
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
MAX_QUESTIONS=5
MAX_CONTENT_LENGTH=5242880
RATELIMIT_STORAGE_URI=memory://
AUTO_CREATE_DB=0
```

## Running With Or Without Anthropic

With an API key:

```powershell
$env:ANTHROPIC_API_KEY="your-key"
python app.py
```

Without an API key, the app still runs. It logs a warning and automatically uses the local fallback question generator and answer evaluator.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The web app runs on `http://127.0.0.1:8000`, backed by PostgreSQL 16. The container runs `flask db upgrade` before starting gunicorn.

## Database Migrations

Create or upgrade the database schema:

```powershell
flask db upgrade
```

Create a new migration after model changes:

```powershell
flask db migrate -m "describe change"
flask db upgrade
```

## Tests

```powershell
python -m unittest discover -s tests
```

The test suite mocks Anthropic calls, verifies fallback scoring/question generation, checks authentication and authorization, and parses sample PDF/DOCX resume fixtures.

## Interview Talking Points

- The app is LLM-first but resilient: missing API keys or malformed LLM responses fall back to deterministic heuristics.
- User data is isolated with `user_id` ownership checks and `403` protection for cross-user access.
- SQLite keeps local development easy, while `DATABASE_URL` enables PostgreSQL in production.
- Rate limits protect expensive LLM routes from abuse.
- CI ensures tests run on every push and pull request.
