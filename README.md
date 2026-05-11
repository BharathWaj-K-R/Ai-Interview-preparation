# AI-Based Interview Preparation System

An intelligent Flask web app that helps students prepare for placements through AI-powered mock interviews.

## What It Does

- Generates interview questions for `Technical`, `HR`, or mixed rounds
- Adapts technical questions using resume text
- Supports text answers and browser voice-to-text input
- Scores each answer for relevance, confidence, sentiment, and technical depth
- Tracks typing speed and includes it in confidence analysis
- Produces a dashboard with topic-wise weak-area recommendations

## Tech Stack

- Python
- Flask
- NLP (sentiment + keyword analysis)
- SQLite
- HTML/CSS/JavaScript

## Project Structure

```text
.
├── app.py
├── interview_app
│   ├── __init__.py
│   ├── db.py
│   ├── routes.py
│   └── services
│       ├── question_engine.py
│       ├── scoring.py
│       └── recommendations.py
├── static
│   ├── css/style.css
│   └── js/interview.js
├── templates
│   ├── base.html
│   ├── index.html
│   ├── interview.html
│   └── dashboard.html
└── tests/test_scoring.py
```

## Quick Start

1. Create and activate a virtual environment
2. Install dependencies
3. Run the app

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## How Scoring Works (MVP)

- `Relevance`: overlap of question keywords with answer keywords
- `Confidence`: answer structure + typing speed - hesitation phrases
- `Sentiment`: VADER sentiment polarity mapped to 0-100
- `Technical Depth`: domain term usage for technical rounds

Final score is a weighted combination of these metrics.

## Why This Is Placement-Strong

- Aligns tightly with AI/Data Science and software interview workflows
- Demonstrates applied NLP + full-stack web engineering
- Easy to explain architecture, model logic, and measurable outcomes
- Includes clear path to extend into production-grade systems

## Suggested Next Upgrades

- Add user authentication and profile history
- Store resume uploads as PDF and parse with OCR/NLP
- Replace heuristic scoring with trained ML models (Scikit-learn/TensorFlow)
- Add webcam-based confidence and emotion tracking
- Build recruiter/admin analytics views
