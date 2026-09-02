from pathlib import Path

from pypdf import PdfReader
from docx import Document


def extract_pdf_text(file_path):
    """Extract text from a PDF resume."""
    reader = PdfReader(file_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n".join(pages).strip()


def extract_docx_text(file_path):
    """Extract text from a DOCX resume."""
    document = Document(file_path)

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n".join(paragraphs)


def extract_resume_text(file_path):
    """Extract text from a PDF or DOCX resume."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".pdf":
        return extract_pdf_text(file_path)

    if extension == ".docx":
        return extract_docx_text(file_path)

    raise ValueError("Unsupported resume format. Use PDF or DOCX.")


if __name__ == "__main__":
    print("Resume parser ready.")
    print("Supported formats: PDF, DOCX")