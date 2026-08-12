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

import phonenumbers

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
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
    "School of Engineering", "School of Business", "School of Design",
    "Polytechnic",
]

# Specific cloud/infra product and tool names that are commonly missing
# from the Jobzilla taxonomy (it's a general jobs dataset, not infra
# -specialized). Without these, spaCy's core NER sees a capitalized
# proper-noun-shaped phrase like "CloudFront" or "AWS EC2" inside a work
# -experience bullet and guesses ORG, since it has no way to know these are
# products, not companies. Tagging them explicitly as skills is strictly
# better than just filtering them out -- "AWS EC2 experience" is genuine
# matching signal that would otherwise be lost entirely.
CUSTOM_TECH_SKILLS = [
    "AWS EC2", "AWS VPC", "AWS EKS", "AWS S3", "AWS IAM", "AWS Lambda",
    "AWS Route53", "AWS VPC Lattice", "AWS Direct Connect", "CloudFront",
    "CloudWatch", "ElastiCache", "IPsec", "Filebeat", "APM Server",
    "Graviton", "GitOps", "Kustomize", "ArgoCD", "Okta", "OpenLDAP",
    "Reserved Instance", "Savings Plan",
]

# The Jobzilla taxonomy includes very generic single-word "skills" (e.g.
# "design", "business", "testing") that also legitimately appear inside
# unrelated company or school names ("Rhode Island School of Design",
# "Feast and Co."). Because skills_ruler runs before core NER with
# overwrite_ents=True, it greedily claims these single words wherever they
# appear -- fragmenting what should have been one clean ORG/EDUCATION span
# and leaving noisy leftover fragments for NER to guess at. Excluding
# overly generic single-word patterns fixes the fragmentation and also
# improves the quality of the skills list itself (these words carry near
# -zero signal as standalone "skills" anyway).
GENERIC_SKILL_BLOCKLIST = {
    "design", "business", "testing", "support", "software", "engineering",
    "mobile", "commerce", "interaction", "workflow", "framework",
    "algorithms", "monitoring", "server", "management", "development",
    "solutions", "systems", "operations", "strategy", "analysis",
    "research", "planning", "reporting", "documentation", "training",
    "leadership", "communication", "presentation", "writing", "editing",
    "languages", "testing",
}


def _pattern_text(pattern) -> str:
    """Reconstruct the plain-text phrase a spaCy pattern matches, for
    blocklist comparison. Handles both string patterns and token-dict list
    patterns (the format the Jobzilla dataset actually uses)."""
    if isinstance(pattern, str):
        return pattern.lower().strip()
    tokens = []
    for tok in pattern:
        value = tok.get("LOWER") or tok.get("TEXT") or tok.get("lower") or ""
        tokens.append(str(value))
    return " ".join(tokens).strip()


def _load_skill_patterns() -> list[dict]:
    """Load the jobzilla skill taxonomy (real dataset) as EntityRuler patterns,
    excluding overly generic single-word terms (see GENERIC_SKILL_BLOCKLIST)."""
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
        pattern = entry.get("pattern")
        if not pattern:
            continue

        text = _pattern_text(pattern)
        if len(text.split()) == 1 and text in GENERIC_SKILL_BLOCKLIST:
            continue

        patterns.append({"label": "SKILL", "pattern": pattern})
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
    skill_ruler.add_patterns(
        [{"label": "SKILL", "pattern": _token_pattern(t)} for t in CUSTOM_TECH_SKILLS]
    )

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
    """Find a phone number anywhere in the text using Google's phonenumbers
    library instead of a regex.

    A regex built around one format (e.g. US-style "(555) 123-4567") will
    silently miss most international formats -- for example a Korean number
    like "(+82) 10-9030-1843" uses a completely different digit grouping
    (2-4-4, not 3-3-4) and doesn't match at all. phonenumbers understands
    real-world numbering plans across ~200 countries instead of guessing at
    a single pattern.
    """
    for match in phonenumbers.PhoneNumberMatcher(text, "US"):
        return phonenumbers.format_number(
            match.number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
    return None


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


TRAILING_NOISE_WORDS = {"and", "of", "the", "with", "&", "in", "for", "to", "at"}

# Entities starting with a common verb are almost always a stray sentence
# fragment NER misfired on (e.g. "gather log data" pulled out of "...which
# gather log data from docker containers"), not a real company/location.
LEADING_VERB_BLOCKLIST = {
    "gather", "gathered", "implement", "implemented", "provision",
    "provisioned", "deploy", "deployed", "manage", "managed", "build",
    "built", "develop", "developed", "establish", "established",
    "introduce", "introduced", "design", "designed", "migrate", "migrated",
    "create", "created", "maintain", "maintained", "optimize", "optimized",
    "reduce", "reduced", "increase", "increased", "enable", "enabled",
    "utilize", "utilized", "leverage", "leveraged", "collect", "collected",
}

# Short 2-3 letter tokens are almost never real company/location names on
# their own (they're usually leftover fragments like "TX", "UI"). "AWS" is
# deliberately NOT allowlisted here even though it's a real company name --
# in résumé bullets it's almost always a platform/technology reference
# ("deployed on AWS"), not a literal employer, so filtering it out of
# companies is the more accurate default.
SHORT_ENTITY_ALLOWLIST = {"ibm", "gcp", "hp", "ge", "3m", "bp", "ea"}


def _looks_like_noise(text: str) -> bool:
    """Filter obvious NER misfires: bullet fragments, sentence-like ORG
    spans, and truncated fragments left over after skills_ruler consumed
    part of the original entity (see GENERIC_SKILL_BLOCKLIST above)."""
    words = text.split()

    if text.startswith(("•", "-")):
        return True
    if len(words) > 6:          # real company/location names are rarely 7+ words
        return True
    if "\n" in text:
        return True
    if len(text) < 3:
        return True
    # Truncated entity: ends in a stray conjunction/preposition, e.g.
    # "Rhode Island School of" or "Feast and" after "Design"/"AI" got
    # peeled off by skills_ruler.
    if words and words[-1].lower().strip(",.") in TRAILING_NOISE_WORDS:
        return True
    # Truncated mid-parenthetical: "RI (Reserved Instance", "Elastic
    # Stack(Filebeat" -- an opening paren with no matching close means the
    # entity span was cut off before the phrase actually ended.
    if text.count("(") != text.count(")"):
        return True
    # Stray sentence fragment: "gather log data" pulled from running prose,
    # not an actual entity.
    if words and words[0].lower() in LEADING_VERB_BLOCKLIST:
        return True
    # Short all-caps fragments ("TX", "UI") are usually noise unless on
    # the allowlist of real short abbreviations.
    if len(words) == 1 and len(text) <= 3 and text.lower() not in SHORT_ENTITY_ALLOWLIST:
        return True

    return False


def extract_entities(doc, labels: tuple[str, ...], char_range: tuple[int, int] | None = None) -> list[str]:
    """Extract entities with the given labels, optionally restricted to a
    character-offset range within the original text (see char_range param
    on parse_cv -- used to keep 'companies' scoped to the Work Experience
    section only, see _find_experience_section below)."""
    seen = []
    for ent in doc.ents:
        if ent.label_ not in labels:
            continue
        if char_range and not (char_range[0] <= ent.start_char < char_range[1]):
            continue
        value = ent.text.strip()
        if value and value not in seen and not _looks_like_noise(value):
            seen.append(value)
    return seen


# Résumés bundle many unrelated organization-shaped mentions together:
# actual employers (Work Experience), certifying bodies (Certificates),
# competition names (Honors & Awards), and community groups (Community).
# spaCy's NER correctly tags all of these as ORG -- it has no concept of
# résumé sections -- so without segmentation, "companies" ends up polluted
# with things like "HashiCorp Korea User Group" or "AWS Certified SysOps
# Administrator" that were never actual employers.
#
# We detect common section header lines and restrict company extraction to
# text between a "Work Experience"-type header and the next section header.
# If no clear header is found (e.g. a short or unconventionally formatted
# CV), we fall back to unrestricted extraction rather than returning nothing.
_EXPERIENCE_HEADER_WORDS = {"work experience", "experience", "professional experience",
                            "employment history", "work history"}
_ANY_SECTION_HEADER_WORDS = _EXPERIENCE_HEADER_WORDS | {
    "honors & awards", "honors and awards", "awards", "honors",
    "certificates", "certifications", "certificate", "certification",
    "education", "community", "skills", "summary", "projects",
    "publications", "languages", "interests", "references",
}
_SECTION_HEADER_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(w) for w in sorted(_ANY_SECTION_HEADER_WORDS, key=len, reverse=True)) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _find_experience_section(text: str) -> tuple[int, int] | None:
    """Return the (start_char, end_char) span of the Work Experience section,
    or None if no recognizable section headers were found at all."""
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        return None

    exp_start = None
    for m in matches:
        if m.group(1).strip().lower() in _EXPERIENCE_HEADER_WORDS:
            exp_start = m.end()
            break
    if exp_start is None:
        return None

    exp_end = len(text)
    for m in matches:
        if m.start() > exp_start:
            exp_end = m.start()
            break

    return (exp_start, exp_end)


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

    # Restrict "companies" to the Work Experience section only (see
    # _find_experience_section) so certifying bodies, award/competition
    # names, and community groups from other sections don't leak in.
    # Falls back to unrestricted extraction if no section headers are
    # detected at all, so simpler/shorter CVs still get a result.
    experience_span = _find_experience_section(text)

    return {
        "name": pick_name(doc, text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "years_of_experience": extract_years_of_experience(text),
        "skills": extract_skills(doc),
        "education": extract_education(doc),
        "companies": extract_entities(doc, ("ORG",), char_range=experience_span),
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