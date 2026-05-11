import math
import re
from typing import Dict, List

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ModuleNotFoundError:
    SentimentIntensityAnalyzer = None


class _FallbackSentimentAnalyzer:
    positive_words = {
        "achieved",
        "active",
        "confident",
        "effective",
        "excellent",
        "good",
        "great",
        "improved",
        "positive",
        "reliable",
        "resolved",
        "strong",
        "success",
    }
    negative_words = {
        "bad",
        "confused",
        "difficult",
        "fail",
        "hard",
        "issue",
        "problem",
        "stress",
        "struggle",
        "uncertain",
        "weak",
        "worried",
    }

    def polarity_scores(self, text: str) -> Dict[str, float]:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if not tokens:
            return {"compound": 0.0}
        pos = sum(1 for token in tokens if token in self.positive_words)
        neg = sum(1 for token in tokens if token in self.negative_words)
        compound = (pos - neg) / max(len(tokens), 1)
        compound = max(-1.0, min(1.0, compound * 5))
        return {"compound": compound}


analyzer = SentimentIntensityAnalyzer() if SentimentIntensityAnalyzer else _FallbackSentimentAnalyzer()

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
}

TECHNICAL_TERMS = {
    "algorithm",
    "api",
    "class",
    "complexity",
    "data",
    "database",
    "deployment",
    "dictionary",
    "flask",
    "function",
    "index",
    "join",
    "model",
    "numpy",
    "object",
    "optimization",
    "overfitting",
    "pipeline",
    "python",
    "query",
    "recall",
    "regression",
    "scikit",
    "sentiment",
    "sql",
    "tensorflow",
    "tokenization",
    "tuple",
    "vector",
}

HESITATION_PHRASES = (
    "i think",
    "maybe",
    "not sure",
    "kind of",
    "sort of",
    "i guess",
)


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _tokenize(text: str) -> List[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if token]


def compute_sentiment_score(answer: str) -> float:
    sentiment = analyzer.polarity_scores(answer)
    compound = sentiment["compound"]
    return round(_clamp((compound + 1) * 50), 2)


def compute_relevance_score(question: str, answer: str) -> float:
    question_tokens = {t for t in _tokenize(question) if t not in STOP_WORDS}
    answer_tokens = {t for t in _tokenize(answer) if t not in STOP_WORDS}

    if not question_tokens:
        return 50.0

    overlap = len(question_tokens.intersection(answer_tokens))
    base = (overlap / len(question_tokens)) * 100

    technical_bonus_terms = len(answer_tokens.intersection(TECHNICAL_TERMS))
    technical_bonus = min(technical_bonus_terms * 4.5, 18.0)

    return round(_clamp(base + technical_bonus), 2)


def compute_typing_score(typing_wpm: float) -> float:
    if typing_wpm <= 0:
        return 25.0

    if typing_wpm < 18:
        return round(_clamp((typing_wpm / 18) * 50), 2)

    if typing_wpm <= 65:
        value = 50 + ((typing_wpm - 18) / 47) * 50
        return round(_clamp(value), 2)

    decay = 100 - (typing_wpm - 65) * 1.15
    return round(_clamp(decay, lower=35.0), 2)


def compute_confidence_score(answer: str, typing_wpm: float) -> float:
    word_count = len(_tokenize(answer))
    answer_length_score = _clamp((word_count / 60) * 100)
    typing_score = compute_typing_score(typing_wpm)

    sentence_breaks = re.split(r"[.!?]+", answer.strip())
    non_empty_sentences = [line for line in sentence_breaks if line.strip()]
    structure_score = _clamp(len(non_empty_sentences) * 22)

    hesitation_count = sum(1 for phrase in HESITATION_PHRASES if phrase in answer.lower())
    hesitation_penalty = hesitation_count * 8.5

    confidence = (0.46 * answer_length_score) + (0.34 * typing_score) + (0.20 * structure_score)
    confidence = confidence - hesitation_penalty

    return round(_clamp(confidence), 2)


def compute_technical_depth(answer: str) -> float:
    tokens = _tokenize(answer)
    if not tokens:
        return 0.0
    hits = sum(1 for token in tokens if token in TECHNICAL_TERMS)
    ratio = hits / math.sqrt(len(tokens))
    return round(_clamp(ratio * 28), 2)


def build_feedback(metrics: Dict[str, float], round_type: str) -> str:
    feedback: List[str] = []

    if metrics["relevance_score"] < 55:
        feedback.append("Try to align your answer more directly with the question intent.")
    else:
        feedback.append("Your answer stayed relevant to the question.")

    if metrics["confidence_score"] < 55:
        feedback.append("Increase confidence by structuring answers in 2-3 crisp points.")
    else:
        feedback.append("Your response style sounded confident and composed.")

    if metrics["sentiment_score"] < 45:
        feedback.append("Use more positive and assertive phrasing to improve impact.")

    if round_type == "technical" and metrics["technical_depth_score"] < 45:
        feedback.append("Add examples, complexity notes, or tradeoffs for stronger technical depth.")

    if not feedback:
        feedback.append("Solid response. Keep maintaining clarity, confidence, and structure.")

    return " ".join(feedback)


def evaluate_response(
    question: str,
    answer: str,
    typing_wpm: float,
    round_type: str,
) -> Dict[str, float | str]:
    sentiment_score = compute_sentiment_score(answer)
    relevance_score = compute_relevance_score(question, answer)
    confidence_score = compute_confidence_score(answer, typing_wpm)
    technical_depth_score = compute_technical_depth(answer) if round_type == "technical" else 50.0

    if round_type == "technical":
        final_score = (
            (0.43 * relevance_score)
            + (0.29 * confidence_score)
            + (0.16 * sentiment_score)
            + (0.12 * technical_depth_score)
        )
    else:
        final_score = (
            (0.38 * relevance_score)
            + (0.34 * confidence_score)
            + (0.28 * sentiment_score)
        )

    result = {
        "sentiment_score": round(sentiment_score, 2),
        "relevance_score": round(relevance_score, 2),
        "confidence_score": round(confidence_score, 2),
        "technical_depth_score": round(technical_depth_score, 2),
        "typing_score": round(compute_typing_score(typing_wpm), 2),
        "final_score": round(_clamp(final_score), 2),
    }
    result["feedback"] = build_feedback(result, round_type)
    return result
