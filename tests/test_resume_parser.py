from pathlib import Path
import unittest

from interview_app.services.resume_parser import parse_resume_file


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestResumeParser(unittest.TestCase):
    def test_parse_docx_fixture(self):
        with (FIXTURE_DIR / "sample_resume.docx").open("rb") as resume:
            text = parse_resume_file(resume, "sample_resume.docx")
        self.assertIn("Python Flask SQL NLP", text)

    def test_parse_pdf_fixture(self):
        with (FIXTURE_DIR / "sample_resume.pdf").open("rb") as resume:
            text = parse_resume_file(resume, "sample_resume.pdf")
        self.assertIn("Python Flask SQL NLP", text)

    def test_rejects_unsupported_file_type(self):
        with self.assertRaises(ValueError):
            parse_resume_file(iter([b"plain text"]), "resume.txt")


if __name__ == "__main__":
    unittest.main()
