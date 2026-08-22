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
        page_texts = []
        for page in doc:
            # page.get_text() (plain "text" mode) concatenates every line
            # into one flat stream with no blank-line separators -- even
            # between two clearly distinct visual entries (e.g. two
            # different certifications, or two different jobs) that are
            # only set apart by vertical spacing/styling in the PDF layout,
            # not by any actual blank line in the text itself. That makes
            # it impossible for downstream section-grouping logic (see
            # cv_parser.py's _group_section_into_entries) to tell where one
            # CV entry ends and the next begins.
            #
            # "blocks" mode returns PyMuPDF's own detected visual text
            # blocks (based on real position/spacing in the page layout).
            # Joining distinct blocks with a blank line reintroduces the
            # paragraph boundaries that plain-text mode discards, while
            # keeping each block's own internal line breaks intact.
            blocks = page.get_text("blocks")
            block_texts = [b[4].rstrip() for b in blocks if b[4].strip()]
            page_texts.append("\n\n".join(block_texts))
        text = "\n\n".join(page_texts)
        doc.close()
        return _normalize_text(text)

    elif ext == ".docx":
        doc = Document(file_path)
        return _normalize_text("\n".join(p.text for p in doc.paragraphs))

    else:
        raise ValueError(f"Unsupported file type: {ext}")