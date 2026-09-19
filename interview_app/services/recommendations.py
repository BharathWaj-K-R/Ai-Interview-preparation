from collections import defaultdict
from typing import Dict, List


TOPIC_RESOURCES = {
    "Python": "Revise data structures, comprehensions, and OOP interview patterns in Python.",
    "Flask": "Practice request lifecycle, app context, Blueprints, and deployment hardening.",
    "Sql": "Revisit joins, indexing, normalization, and query optimization exercises.",
    "Nlp": "Review tokenization, vectorization, sentiment workflows, and model evaluation metrics.",
    "Machine Learning": "Strengthen understanding of model selection, validation, and bias-variance tradeoff.",
    "Deep Learning": "Practice neural network fundamentals, activations, and overfitting prevention techniques.",
    "Behavioral": "Use STAR format and rehearse concise impact-focused stories from your experience.",
}


def weak_topics_from_responses(responses: List[Dict]) -> List[Dict]:
    buckets = defaultdict(list)
    for row in responses:
        buckets[row["question_topic"]].append(float(row["final_score"]))

    weak_topics = []
    for topic, scores in buckets.items():
        avg_score = sum(scores) / len(scores)
        if avg_score < 65:
            weak_topics.append(
                {
                    "topic": topic,
                    "avg_score": round(avg_score, 2),
                    "recommendation": TOPIC_RESOURCES.get(
                        topic,
                        "Practice this topic with structured mock questions and timed responses.",
                    ),
                }
            )

    weak_topics.sort(key=lambda x: x["avg_score"])
    return weak_topics


def strengths_from_responses(responses: List[Dict]) -> List[str]:
    strengths = []
    if not responses:
        return strengths

    avg_confidence = sum(float(row["confidence_score"]) for row in responses) / len(responses)
    avg_sentiment = sum(float(row["sentiment_score"]) for row in responses) / len(responses)
    avg_relevance = sum(float(row["relevance_score"]) for row in responses) / len(responses)

    if avg_relevance >= 70:
        strengths.append("You maintain strong relevance to most interview questions.")
    if avg_confidence >= 70:
        strengths.append("You communicate with steady confidence and answer structure.")
    if avg_sentiment >= 70:
        strengths.append("Your tone is positive and interviewer-friendly.")

    return strengths
