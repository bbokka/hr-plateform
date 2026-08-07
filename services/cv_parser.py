"""Stage 3: structured field extraction from raw CV text.

Pipeline (mirrors how junior/mid NLP engineers actually parse resumes):
  - spaCy NER            -> companies (ORG), locations (GPE), dates
  - Regex                -> email, phone, years of experience (spaCy misses these)
  - EntityRuler          -> skills (loaded from the real jobzilla taxonomy, not a
                            hand-typed list) and education (degree + school terms)
  - First-line heuristic -> name (more reliable than NER across non-Western names)

Returns a structured dict ready to store on Candidate.cv_parsed_data and to feed
the Stage 4 embeddings/matching pipeline.
"""
import json
import re
from pathlib import Path

import spacy

from scripts.download_skills import SOURCE_URL
from services.cv_extraction import extract_text_from_cv

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SKILLS_FILE = DATA_DIR / "jz_skill_patterns.jsonl"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
)
YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:years|yrs)", re.IGNORECASE)

DEGREE_ABBREVIATIONS = ["B.S.", "B.A.", "B.E.", "B.Tech", "M.S.", "M.A.", "M.E.",
                        "M.Tech", "M.B.A.", "MBA", "Ph.D.", "PhD", "B.Sc.", "M.Sc."]

DEGREE_PHRASES = [
    "Bachelor of Science", "Bachelor of Arts", "Bachelor of Engineering",
    "Bachelor of Technology", "Master of Science", "Master of Arts",
    "Master of Engineering", "Master of Technology",
    "Master of Business Administration", "Doctorate", "Associate degree",
    "Bachelor's degree", "Master's degree",
]

SCHOOL_KEYWORDS = [
    "University", "College", "Institute of Technology", "Academy",
    "School of Engineering", "School of Business", "Polytechnic",
]


def _load_skill_patterns() -> list[dict]:
    """Load the jobzilla skill taxonomy (real dataset) as EntityRuler patterns."""
    if not SKILLS_FILE.exists():
        from scripts.download_skills import download_skills
        download_skills()

    patterns = []
    for line in SKILLS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "pattern" not in entry or not entry["pattern"]:
            continue
        patterns.append({"label": "SKILL", "pattern": entry["pattern"]})
    return patterns


def _token_pattern(phrase: str) -> list[dict]:
    return [{"LOWER": token.lower()} for token in phrase.split()]


def _build_nlp():
    nlp = spacy.load("en_core_web_sm")

    # Skills ruler fed by the industry taxonomy (2k+ real terms).
    # Runs BEFORE core NER with overwrite_ents=True so our explicit skill
    # matches always win over NER's (often wrong) guesses on the same span.
    skill_ruler = nlp.add_pipe("entity_ruler", name="skills_ruler",
                               before="ner", config={"overwrite_ents": True})
    skill_ruler.add_patterns(_load_skill_patterns())

    # Education ruler: degree levels + school-related keywords.
    # IMPORTANT: also runs BEFORE core NER with overwrite_ents=True.
    # Previously this ran AFTER ner with overwrite_ents=False, which meant
    # if NER mis-tagged something like "B.S." as GPE, our correct EDUCATION
    # label was silently discarded (NER's wrong guess always won). Running
    # before NER with override enabled fixes that, matching the pattern
    # already used successfully for skills_ruler above.
    edu_ruler = nlp.add_pipe("entity_ruler", name="edu_ruler",
                             before="ner", config={"overwrite_ents": True})
    edu_patterns = [{"label": "EDUCATION", "pattern": _token_pattern(p)} for p in DEGREE_PHRASES]
    edu_patterns += [{"label": "EDUCATION", "pattern": _token_pattern(a)} for a in DEGREE_ABBREVIATIONS]
    edu_patterns += [{"label": "EDUCATION", "pattern": _token_pattern(k)} for k in SCHOOL_KEYWORDS]
    edu_ruler.add_patterns(edu_patterns)

    return nlp


_NLP = _build_nlp()


def extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group(0).lower() if match else None


def extract_phone(text: str) -> str | None:
    match = PHONE_RE.search(text)
    return match.group(0).strip() if match else None


def extract_years_of_experience(text: str) -> int | None:
    matches = YEARS_RE.findall(text)
    if not matches:
        return None
    return max(int(y) for y in matches)


def extract_education(doc) -> list[str]:
    seen = []
    for ent in doc.ents:
        if ent.label_ == "EDUCATION":
            value = ent.text.strip()
            if value and value not in seen:
                seen.append(value)
    return seen


def extract_skills(doc) -> list[str]:
    seen = []
    for ent in doc.ents:
        if ent.label_ == "SKILL":
            value = ent.text.strip()
            if value and value not in seen:
                seen.append(value)
    return seen


def extract_entities(doc, labels: tuple[str, ...]) -> list[str]:
    seen = []
    for ent in doc.ents:
        if ent.label_ in labels:
            value = ent.text.strip()
            if value and value not in seen:
                seen.append(value)
    return seen


def pick_name(doc, text: str) -> str | None:
    """Best-guess candidate name.

    Résumés near-universally put the name on the first non-empty line —
    this is a stronger, culture-agnostic signal than spaCy's PERSON NER,
    which is trained mostly on Western names and can misfire on others
    (e.g. tagging a GitHub handle as a name instead of a Korean name like
    "Byungjin Park"). We trust the first-line heuristic first and only
    fall back to NER if that line doesn't look name-like.
    """
    first_line = next((l.strip() for l in text.splitlines() if l.strip()), "")

    looks_like_name = (
        first_line
        and 2 <= len(first_line.split()) <= 4
        and len(first_line) <= 40
        and not re.search(r"\d", first_line)
        and "@" not in first_line
        and not any(c in first_line for c in ("|", ":", "•"))
    )
    if looks_like_name:
        return first_line

    # Fallback: earliest PERSON entity from spaCy NER
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    return None


def parse_cv(raw_text: str) -> dict:
    """Run the full Stage 3 pipeline over extracted text -> structured JSON."""
    text = (raw_text or "").strip()
    if not text:
        return {}

    doc = _NLP(text)

    return {
        "name": pick_name(doc, text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "years_of_experience": extract_years_of_experience(text),
        "skills": extract_skills(doc),
        "education": extract_education(doc),
        "companies": extract_entities(doc, ("ORG",)),
        "locations": extract_entities(doc, ("GPE",)),
    }


def parse_cv_file(file_path: str) -> dict:
    """Extract text from an uploaded file, then run the pipeline."""
    raw_text = extract_text_from_cv(file_path)
    return parse_cv(raw_text)


if __name__ == "__main__":
    import sys
    result = parse_cv_file(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n({SOURCE_URL})")

def _looks_like_noise(text: str) -> bool:
    """Filter obvious NER misfires: bullet fragments, sentence-like ORG spans."""
    return (
        text.startswith(("•", "-"))
        or len(text.split()) > 6          # real company names are rarely 7+ words
        or "\n" in text
    )

def extract_entities(doc, labels: tuple[str, ...]) -> list[str]:
    seen = []
    for ent in doc.ents:
        if ent.label_ in labels:
            value = ent.text.strip()
            if value and value not in seen and not _looks_like_noise(value):
                seen.append(value)
    return seen