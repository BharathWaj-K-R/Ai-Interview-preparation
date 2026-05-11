import unittest

from interview_app.services.question_engine import generate_questions


class TestQuestionEngine(unittest.TestCase):
    def test_technical_questions_prioritize_explicit_skills(self):
        questions = generate_questions(
            round_type="technical",
            resume_text="",
            skills_text="Python, SQL",
            count=3,
        )
        joined = " ".join(item["text"] for item in questions).lower()
        self.assertIn("you listed python", joined)
        self.assertIn("you listed sql", joined)

    def test_unknown_skill_creates_custom_skill_question(self):
        questions = generate_questions(
            round_type="technical",
            resume_text="",
            skills_text="Kubernetes",
            count=1,
        )
        self.assertIn("kubernetes", questions[0]["text"].lower())
        self.assertIn("project", questions[0]["text"].lower())

    def test_hr_round_uses_resume_and_skills_context(self):
        questions = generate_questions(
            round_type="hr",
            resume_text="Built a real-time attendance system with Flask and SQLite for 1200 students.",
            skills_text="Flask",
            count=2,
        )
        joined = " ".join(item["text"] for item in questions).lower()
        self.assertTrue("you listed flask" in joined or "resume point" in joined)


if __name__ == "__main__":
    unittest.main()
