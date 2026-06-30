from io import BytesIO
from pathlib import Path
from typing import BinaryIO

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}


def _extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def parse_resume_file(file_obj: BinaryIO, filename: str) -> str:
    ext = _extension(filename)
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise ValueError("Only .pdf and .docx resume uploads are supported.")

    data = file_obj.read()
    if not data:
        return ""

    if ext == ".pdf":
        return _parse_pdf(data)
    return _parse_docx(data)


def _parse_pdf(data: bytes) -> str:
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise RuntimeError("pdfplumber is required to parse PDF resumes.") from exc

    pages_text = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text.strip())
    return "\n".join(pages_text)


def _parse_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ModuleNotFoundError as exc:
        raise RuntimeError("python-docx is required to parse DOCX resumes.") from exc

    document = Document(BytesIO(data))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)
