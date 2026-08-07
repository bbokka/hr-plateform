from pathlib import Path
import pymupdf  # PyMuPDF
from docx import Document

def extract_text_from_cv(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        doc = pymupdf.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text

    elif ext == ".docx":
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    else:
        raise ValueError(f"Unsupported file type: {ext}")