"""Tests for services/cv_extraction.py -- specifically the soft-hyphen
normalization fix.

LaTeX-generated CVs (e.g. the Awesome-CV template) commonly render dashes
and hyphenation points using the Unicode soft hyphen (U+00AD) instead of a
plain hyphen. It's invisible when rendered but breaks downstream regexes
(e.g. cv_parser's date-range detector, which expects a literal "-", "-",
or "-") if the raw codepoint survives into the extracted text.

Note: we can't reliably reproduce a literal U+00AD through a real generated
PDF round-trip -- PyMuPDF's own text insertion/extraction normalizes it
away at the font level, so a fixture PDF built with page.insert_text()
would already come back clean and the test would pass without exercising
the fix at all. These tests instead verify the normalization directly: a
pure unit test against the string helper, plus full extract_text_from_cv()
entry-point tests with the underlying PDF/DOCX libraries stubbed out so we
control the exact extracted codepoints.
"""
from unittest.mock import MagicMock, patch

from services.cv_extraction import _normalize_text, extract_text_from_cv

SOFT_HYPHEN = "\u00ad"


def test_normalize_text_replaces_soft_hyphen_with_regular_hyphen():
    raw = f"Sep. 2023 {SOFT_HYPHEN} Mar. 2024"
    assert _normalize_text(raw) == "Sep. 2023 - Mar. 2024"


def test_normalize_text_handles_mid_word_soft_hyphen():
    raw = f"Co{SOFT_HYPHEN}founder & Engineer"
    assert _normalize_text(raw) == "Co-founder & Engineer"


def test_normalize_text_is_a_no_op_when_no_soft_hyphens_present():
    raw = "Regular text with a normal - hyphen."
    assert _normalize_text(raw) == raw


def test_extract_text_from_cv_normalizes_pdf_text(tmp_path):
    """Full entry-point test: a .pdf whose underlying text contains a
    literal soft hyphen should come back normalized. PyMuPDF is stubbed so
    we control the exact extracted codepoints (see module docstring)."""
    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")  # content is irrelevant; pymupdf.open is mocked

    fake_page = MagicMock()
    # get_text("blocks") returns (x0, y0, x1, y1, text, block_no, block_type)
    # tuples -- see extract_text_from_cv's blocks-mode extraction.
    fake_page.get_text.return_value = [
        (0, 0, 100, 10, f"Sep. 2023 {SOFT_HYPHEN} Mar. 2024\n", 0, 0),
    ]
    fake_doc = MagicMock()
    fake_doc.__iter__.return_value = iter([fake_page])

    with patch("services.cv_extraction.pymupdf.open", return_value=fake_doc):
        text = extract_text_from_cv(str(pdf_path))

    assert SOFT_HYPHEN not in text
    assert text == "Sep. 2023 - Mar. 2024"
    fake_doc.close.assert_called_once()


def test_extract_text_from_cv_preserves_block_boundaries_as_blank_lines(tmp_path):
    """Regression test: PyMuPDF's plain 'text' extraction mode collapses
    every line into one flat stream with no blank-line separators at all,
    even between two visually and logically distinct CV entries (e.g. two
    separate certifications, styled with vertical spacing between them in
    the PDF but no actual blank line in the text). cv_parser.py's
    section-entry grouping (_group_section_into_entries) depends on
    real blank lines marking where one entry ends and the next begins, so
    extraction must use PyMuPDF's 'blocks' mode -- which reflects the PDF's
    actual visual layout -- and join distinct blocks with a blank line."""
    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    fake_page = MagicMock()
    fake_page.get_text.return_value = [
        (0, 0, 100, 10, "PROJET(PAQ-DGSE) (2024)\nAttestation a la formation\n", 0, 0),
        (0, 20, 100, 30, "Company Program avec\nINJAZ Tunisia (05/2024)\n", 1, 0),
    ]
    fake_doc = MagicMock()
    fake_doc.__iter__.return_value = iter([fake_page])

    with patch("services.cv_extraction.pymupdf.open", return_value=fake_doc):
        text = extract_text_from_cv(str(pdf_path))

    assert "\n\n" in text
    first_block, second_block = text.split("\n\n")
    assert first_block == "PROJET(PAQ-DGSE) (2024)\nAttestation a la formation"
    assert second_block == "Company Program avec\nINJAZ Tunisia (05/2024)"


def test_extract_text_from_cv_normalizes_docx_text(tmp_path):
    docx_path = tmp_path / "fake.docx"
    docx_path.write_bytes(b"fake docx bytes")  # irrelevant; Document is mocked

    fake_paragraph = MagicMock()
    fake_paragraph.text = f"Co{SOFT_HYPHEN}founder & Engineer"
    fake_doc = MagicMock()
    fake_doc.paragraphs = [fake_paragraph]

    with patch("services.cv_extraction.Document", return_value=fake_doc):
        text = extract_text_from_cv(str(docx_path))

    assert SOFT_HYPHEN not in text
    assert text == "Co-founder & Engineer"


def test_extract_text_from_cv_raises_on_unsupported_extension(tmp_path):
    bad_path = tmp_path / "resume.txt"
    bad_path.write_text("hello")
    try:
        extract_text_from_cv(str(bad_path))
        assert False, "expected ValueError for unsupported extension"
    except ValueError:
        pass