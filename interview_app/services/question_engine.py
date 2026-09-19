import logging
import random
import re
from typing import Dict, List

from .ai_client import AIClientError, AnthropicAIClient, extract_json_payload


logger = logging.getLogger(__name__)


TECHNICAL_QUESTION_BANK: Dict[str, List[str]] = {
    "python": [
        "Explain the difference between a list and a tuple in Python.",
        "When would you use a dictionary comprehension?",
        "How does Python's garbage collection work at a high level?",
    ],
    "flask": [
        "What is the purpose of Blueprints in Flask?",
        "How do request and application contexts differ in Flask?",
        "How would you secure a Flask application before production?",
    ],
    "sql": [
        "Explain the difference between INNER JOIN and LEFT JOIN.",
        "How would you optimize a slow query in a relational database?",
        "What is normalization, and when can denormalization help?",
    ],
    "nlp": [
        "What are tokenization and stemming, and why are they useful?",
        "How would you evaluate a sentiment analysis model?",
        "What is the difference between TF-IDF and word embeddings?",
    ],
    "machine learning": [
        "Explain bias-variance tradeoff with an example.",
        "How do precision, recall, and F1-score differ?",
        "When would you choose a tree-based model over linear regression?",
    ],
    "deep learning": [
        "Why do we use activation functions in neural networks?",
        "What is overfitting, and how does dropout reduce it?",
        "How would you explain backpropagation to a beginner?",
    ],
}

HR_QUESTIONS: List[str] = [
    "Tell me about yourself.",
    "Describe a challenge you faced and how you handled it.",
    "Why do you want to join our company?",
    "How do you handle pressure and deadlines?",
    "Describe a time you worked in a team with conflict.",
    "What are your strengths and one area you are improving?",
]

SKILL_ALIASES = {
    "python": ["python", "pandas", "numpy"],
    "flask": ["flask", "django", "fastapi", "api"],
    "sql": ["sql", "mysql", "postgresql", "sqlite", "database"],
    "nlp": ["nlp", "text mining", "sentiment", "tokenization", "bert"],
    "machine learning": ["machine learning", "ml", "scikit-learn", "regression", "classification"],
    "deep learning": ["deep learning", "tensorflow", "pytorch", "cnn", "rnn"],
}


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            ordered.append(value.strip())
    return ordered


def _normalize_skill(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _canonical_skill(value: str) -> str:
    cleaned = _normalize_skill(value)
    if not cleaned:
        return ""

    for skill, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            if cleaned == _normalize_skill(alias):
                return skill
    return cleaned


def _extract_skills_from_text(text: str) -> List[str]:
    if not text.strip():
        return []

    lowered = text.lower()
    hits: List[str] = []
    for skill, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            pattern = rf"\b{re.escape(alias.lower())}\b"
            if re.search(pattern, lowered):
                hits.append(skill)
                break
    return _dedupe_keep_order(hits)


def _extract_explicit_skills(skills_text: str) -> List[str]:
    if not skills_text.strip():
        return []

    raw_parts = re.split(r"[,/\n;|]+", skills_text)
    canonical = [_canonical_skill(part) for part in raw_parts if part.strip()]
    return _dedupe_keep_order(canonical)


def _resume_highlight_lines(resume_text: str) -> List[str]:
    if not resume_text.strip():
        return []

    highlights: List[str] = []
    lines = re.split(r"[\n\r]+", resume_text)
    for line in lines:
        cleaned = line.strip(" -\t")
        if len(cleaned) < 18:
            continue
        word_count = len(cleaned.split())
        if 4 <= word_count <= 20:
            highlights.append(cleaned)

    if not highlights:
        sentences = re.split(r"(?<=[.!?])\s+", resume_text.strip())
        for sentence in sentences:
            cleaned = sentence.strip()
            if 7 <= len(cleaned.split()) <= 24:
                highlights.append(cleaned)

    return _dedupe_keep_order(highlights)[:3]


def _build_skill_linked_question(skill: str) -> Dict[str, str]:
    canonical_skill = _canonical_skill(skill)
    prompts = TECHNICAL_QUESTION_BANK.get(canonical_skill, [])

    if prompts:
        question = random.choice(prompts)
        personalized = f"{question} (You listed {canonical_skill.title()} in your profile.)"
        return {
            "topic": canonical_skill.title(),
            "round_type": "technical",
            "text": personalized,
        }

    generic = (
        f"You mentioned {skill.title()} in your skills. "
        "Explain one project where you used it, key decisions you made, and tradeoffs."
    )
    return {"topic": skill.title(), "round_type": "technical", "text": generic}


def _technical_questions_from_profile(resume_text: str, skills_text: str, count: int) -> List[Dict[str, str]]:
    explicit_skills = _extract_explicit_skills(skills_text)
    resume_skills = _extract_skills_from_text(resume_text)
    prioritized_skills = _dedupe_keep_order(explicit_skills + resume_skills)

    questions: List[Dict[str, str]] = []
    for skill in prioritized_skills:
        questions.append(_build_skill_linked_question(skill))
        if len(questions) >= count:
            return questions

    for line in _resume_highlight_lines(resume_text):
        questions.append(
            {
                "topic": "Resume Project",
                "round_type": "technical",
                "text": (
                    f"Based on your resume line '{line}', explain your exact technical contribution, "
                    "the architecture, and how you measured success."
                ),
            }
        )
        if len(questions) >= count:
            return questions

    return questions


def _fallback_technical_pool() -> List[Dict[str, str]]:
    pool: List[Dict[str, str]] = []
    for topic, prompts in TECHNICAL_QUESTION_BANK.items():
        for prompt in prompts:
            pool.append({"topic": topic.title(), "round_type": "technical", "text": prompt})
    random.shuffle(pool)
    return pool


def _resume_hr_questions(resume_text: str, skills_text: str) -> List[Dict[str, str]]:
    questions: List[Dict[str, str]] = []
    skills = _dedupe_keep_order(_extract_explicit_skills(skills_text) + _extract_skills_from_text(resume_text))
    highlights = _resume_highlight_lines(resume_text)

    if skills:
        for skill in skills[:2]:
            questions.append(
                {
                    "topic": "Behavioral",
                    "round_type": "hr",
                    "text": (
                        f"You listed {skill.title()} in your profile. "
                        "Describe a situation where your use of this skill created measurable impact."
                    ),
                }
            )

    for line in highlights[:2]:
        questions.append(
            {
                "topic": "Behavioral",
                "round_type": "hr",
                "text": (
                    f"Walk me through this resume point: '{line}'. "
                    "What was challenging, and what did you personally own?"
                ),
            }
        )

    return questions


def generate_questions_fallback(
    round_type: str,
    resume_text: str,
    count: int = 5,
    skills_text: str = "",
) -> List[Dict[str, str]]:
    requested_round = round_type.lower()
    if requested_round not in {"technical", "hr", "both"}:
        requested_round = "both"

    if requested_round == "both":
        technical = generate_questions("technical", resume_text, count=3, skills_text=skills_text)
        hr = generate_questions("hr", resume_text, count=2, skills_text=skills_text)
        combined = technical + hr
        random.shuffle(combined)
        return combined[:count]

    if requested_round == "hr":
        profile_linked = _resume_hr_questions(resume_text, skills_text)
        pool = HR_QUESTIONS.copy()
        random.shuffle(pool)
        general = [
            {"topic": "Behavioral", "round_type": "hr", "text": question}
            for question in pool[:count]
        ]
        merged = profile_linked + general
        unique: List[Dict[str, str]] = []
        seen = set()
        for item in merged:
            key = item["text"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
            if len(unique) >= count:
                break
        return unique

    profile_linked = _technical_questions_from_profile(resume_text, skills_text, count=count)
    fallback = _fallback_technical_pool()

    combined = profile_linked + fallback
    unique: List[Dict[str, str]] = []
    seen = set()
    for item in combined:
        key = item["text"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= count:
            break
    return unique



def _validate_llm_questions(payload: object, round_type: str, count: int) -> List[Dict[str, str]]:
    if not isinstance(payload, list):
        raise AIClientError("Question response must be a JSON array.")

    questions: List[Dict[str, str]] = []
    normalized_round = "hr" if round_type == "hr" else "technical"
    for item in payload:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        topic = str(item.get("topic", "")).strip() or "General"
        difficulty = str(item.get("difficulty", "")).strip() or "medium"
        if not question:
            continue

        questions.append(
            {
                "topic": topic.title(),
                "round_type": normalized_round,
                "difficulty": difficulty.lower(),
                "text": question,
            }
        )
        if len(questions) >= count:
            break

    if not questions:
        raise AIClientError("LLM did not return any usable questions.")
    return questions


def _generate_questions_with_llm(
    round_type: str,
    resume_text: str,
    skills_text: str,
    count: int,
) -> List[Dict[str, str]]:
    client = AnthropicAIClient()
    if not client.available:
        raise AIClientError("Anthropic client is unavailable.")

    prompt = f"""
Generate exactly {count} interview questions for a placement mock interview.

Candidate resume text:
{resume_text or "No resume text provided."}

Explicit skills:
{skills_text or "No explicit skills provided."}

Requested round type:
{round_type}

Rules:
- Questions must be directly related to the resume and skills whenever possible.
- Include a mix of conceptual, project-based, and practical questions for technical rounds.
- Include behavioral questions tied to resume experience for HR rounds.
- Return only valid JSON, with no markdown.
- JSON format: [{{"question": "...", "topic": "...", "difficulty": "easy|medium|hard"}}]
"""
    system = "You are an expert technical recruiter. Return strict JSON only."
    raw = client.complete_text(prompt=prompt, system=system)
    payload = extract_json_payload(raw)
    return _validate_llm_questions(payload, round_type=round_type, count=count)


def generate_questions(
    round_type: str,
    resume_text: str,
    count: int = 5,
    skills_text: str = "",
) -> List[Dict[str, str]]:
    try:
        return _generate_questions_with_llm(
            round_type=round_type,
            resume_text=resume_text,
            skills_text=skills_text,
            count=count,
        )
    except Exception as exc:
        logger.warning("Falling back to heuristic question generation: %s", exc)
        return generate_questions_fallback(
            round_type=round_type,
            resume_text=resume_text,
            skills_text=skills_text,
            count=count,
        )
