import re
import unittest
from uuid import uuid4

from interview_app import create_app


class TestAuthFlow(unittest.TestCase):
    def setUp(self):
        db_name = f"instance/test_auth_{uuid4().hex}.sqlite3"
        self.app = create_app({"TESTING": True, "DATABASE": db_name, "SECRET_KEY": "test-secret"})
        self.client = self.app.test_client()

    def register(self, client, email):
        return client.post(
            "/register",
            data={"email": email, "password": "password123"},
            follow_redirects=False,
        )

    def test_home_requires_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_register_then_start_interview(self):
        response = self.register(self.client, f"student-{uuid4().hex}@example.com")
        self.assertEqual(response.status_code, 302)

        start = self.client.post(
            "/start",
            data={
                "candidate_name": "Student",
                "round_type": "technical",
                "resume_text": "Built Flask and SQL projects.",
                "skills_text": "Flask, SQL",
            },
            follow_redirects=False,
        )
        self.assertEqual(start.status_code, 302)
        self.assertRegex(start.headers["Location"], r"/interview/\d+/0")

    def test_other_user_cannot_access_dashboard(self):
        client_one = self.app.test_client()
        client_two = self.app.test_client()
        self.register(client_one, f"owner-{uuid4().hex}@example.com")
        start = client_one.post(
            "/start",
            data={
                "candidate_name": "Owner",
                "round_type": "technical",
                "resume_text": "Python project",
                "skills_text": "Python",
            },
        )
        session_id = int(re.search(r"/interview/(\d+)/0", start.headers["Location"]).group(1))

        self.register(client_two, f"other-{uuid4().hex}@example.com")
        response = client_two.get(f"/dashboard/{session_id}")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
