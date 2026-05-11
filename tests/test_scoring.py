import unittest

from interview_app.services.scoring import (
    compute_confidence_score,
    compute_relevance_score,
    compute_sentiment_score,
    evaluate_response,
)


class TestScoring(unittest.TestCase):
    def test_sentiment_score_is_in_valid_range(self):
        score = compute_sentiment_score("I am excited and confident about solving this problem.")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_relevance_increases_with_keyword_overlap(self):
        question = "Explain difference between list and tuple in Python."
        weak_answer = "I like coding and building projects."
        strong_answer = "In Python, list is mutable while tuple is immutable."
        weak_score = compute_relevance_score(question, weak_answer)
        strong_score = compute_relevance_score(question, strong_answer)
        self.assertGreater(strong_score, weak_score)

    def test_confidence_penalizes_hesitation_language(self):
        hesitant = "I think maybe this is correct, not sure though."
        assertive = "I will solve this by outlining assumptions and choosing an optimal approach."
        hesitant_score = compute_confidence_score(hesitant, typing_wpm=35)
        assertive_score = compute_confidence_score(assertive, typing_wpm=35)
        self.assertGreater(assertive_score, hesitant_score)

    def test_evaluate_response_returns_expected_keys(self):
        result = evaluate_response(
            question="How do you optimize SQL queries?",
            answer="I review indexes, execution plans, and reduce full table scans.",
            typing_wpm=42,
            round_type="technical",
        )
        expected_keys = {
            "sentiment_score",
            "relevance_score",
            "confidence_score",
            "technical_depth_score",
            "typing_score",
            "final_score",
            "feedback",
        }
        self.assertTrue(expected_keys.issubset(set(result.keys())))


if __name__ == "__main__":
    unittest.main()
