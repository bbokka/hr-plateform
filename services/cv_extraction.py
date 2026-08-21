from pathlib import Path
import pymupdf  # PyMuPDF
from docx import Document

# LaTeX-generated CVs (e.g. the Awesome-CV template) commonly render dashes
# and hyphenation points using the Unicode soft hyphen (U+00AD) instead of a
# plain "-", en dash "-", or em dash. It's invisible when rendered, but once
# extracted as plain text it silently breaks every downstream regex that
# expects a normal hyphen -- e.g. a date range like "Sep. 2023 <soft-hyphen>
# Mar. 2024" won't match a date-range pattern built around "-"/"-"/"-",
# and compound words like "co<soft-hyphen>founder" look fine visually but
# aren't the same characters a regex or taxonomy match expects. Normalizing
# it to a plain hyphen at the extraction boundary fixes this everywhere
# downstream instead of needing every consuming regex to special-case it.
_SOFT_HYPHEN = "\u00ad"


def _normalize_text(text: str) -> str:
    return text.replace(_SOFT_HYPHEN, "-")


def extract_text_from_cv(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        doc = pymupdf.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return _normalize_text(text)

    elif ext == ".docx":
        doc = Document(file_path)
        return _normalize_text("\n".join(p.text for p in doc.paragraphs))

    else:
        raise ValueError(f"Unsupported file type: {ext}")