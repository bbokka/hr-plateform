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
    # Cloud / AWS
    "AWS", "Amazon Web Services", "AWS EC2", "AWS VPC", "AWS EKS",
    "AWS S3", "AWS IAM", "AWS Lambda", "AWS Route53", "AWS VPC Lattice",
    "AWS Direct Connect", "AWS ECR", "AWS ECS", "AWS RDS",
    "CloudFront", "CloudWatch", "ElastiCache", "Graviton",
    "Reserved Instance", "Savings Plan",

    # Containers / orchestration / IaC
    "Kubernetes", "Terraform", "Kustomize", "ArgoCD", "GitOps",
    "Docker", "Rancher", "Ansible", "Packer", "Atlantis",
    "DC/OS", "OpenVPN",

    # Service mesh / networking / security
    "Istio", "Cilium", "Kuma", "Consul", "Vault", "IPsec",
    "Okta", "OpenLDAP", "LDAP", "Kong",

    # Observability / data infrastructure
    "Kafka", "Elastic Stack", "Filebeat", "Heartbeat", "APM Server",
    "Logstash", "Elasticsearch", "Kibana", "Telegraf", "InfluxDB",
    "Grafana", "CollectD",

    # Application / platform technologies explicitly present in the CV
    "CircleCI", "Node.js", "Koa", "REST API", "API", "microservices",
    "serverless", "Android",

    # Developer tooling / platforms explicitly present in the CV
    "GitHub", "Slack", "Google Workspace", "Linux", "macOS", "zsh",
    "Tmux", "NeoVim", "chezmoi", "Claude Code", "Machine Learning",
    "ML", "AI",
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
    "languages", "testing", "queue", "play", "console", "google",
    "computer science", "university",
}

# Canonical names prevent duplicate skills such as "Terraform"/"terraform",
# "Docker"/"docker", "Security"/"security", and "Amazon Web Services"/"AWS".
SKILL_CANONICAL_MAP = {
    "aws": "AWS",
    "amazon web services": "AWS",
    "aws route53": "AWS Route53",
    "aws ec2": "AWS EC2",
    "aws vpc": "AWS VPC",
    "aws eks": "AWS EKS",
    "aws s3": "AWS S3",
    "aws iam": "AWS IAM",
    "aws lambda": "AWS Lambda",
    "aws vpc lattice": "AWS VPC Lattice",
    "aws direct connect": "AWS Direct Connect",
    "aws ecr": "AWS ECR",
    "aws ecs": "AWS ECS",
    "aws rds": "AWS RDS",
    "terraform": "Terraform",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "security": "Security",
    "gitops": "GitOps",
    "kustomize": "Kustomize",
    "argocd": "ArgoCD",
    "neovim": "NeoVim",
    "node.js": "Node.js",
    "ml": "ML",
    "ai": "AI",
    "machine learning": "Machine Learning",
    "google workspace": "Google Workspace",
}

# These are not useful standalone skills in a CV. Most are ordinary nouns
# extracted by a broad taxonomy from phrases such as "Google Play" or
# "Dead Letter Queue".
SKILL_FALSE_POSITIVE_EXACT = {
    "play",
    "queue",
    "console",
    "google",
    "computer science",
    "university",
}

# Maps a canonicalized technical skill (i.e. the exact strings extract_skills
# can return, post SKILL_CANONICAL_MAP) to the higher-level professional
# expertise domain(s) it signals. This is deliberately a many-to-many mapping:
# a single skill like "Terraform" is genuine evidence of both "Infrastructure
# as Code" and "DevOps", and a single expertise domain is usually only
# credible once several of its trigger skills show up together on a CV.
#
# Expertise is intentionally *derived* from the technical skills list rather
# than pattern-matched against free-text prose (e.g. the CV's Summary
# paragraph): summaries are written in wildly inconsistent phrasing across
# CVs ("DevOps & SRE practices" vs "site reliability" vs "platform
# engineering"), whereas the technical skill list is already a normalized,
# deduplicated signal we trust. Deriving from it keeps expertise deterministic
# and avoids adding a second, fuzzier NLP surface on top of an already large
# rules stack.
SKILL_TO_EXPERTISE = {
    # Cloud Architecture
    "AWS": ["Cloud Architecture"],
    "AWS EC2": ["Cloud Architecture"],
    "AWS VPC": ["Cloud Architecture"],
    "AWS EKS": ["Cloud Architecture", "Container Orchestration"],
    "AWS S3": ["Cloud Architecture"],
    "AWS IAM": ["Cloud Architecture", "Security Engineering"],
    "AWS Lambda": ["Cloud Architecture", "Software Architecture"],
    "AWS Route53": ["Cloud Architecture"],
    "AWS VPC Lattice": ["Cloud Architecture"],
    "AWS Direct Connect": ["Cloud Architecture"],
    "AWS ECR": ["Cloud Architecture"],
    "AWS ECS": ["Cloud Architecture", "Container Orchestration"],
    "AWS RDS": ["Cloud Architecture"],
    "CloudFront": ["Cloud Architecture"],
    "CloudWatch": ["Cloud Architecture", "Observability"],
    "ElastiCache": ["Cloud Architecture"],
    "Graviton": ["Cloud Architecture"],
    "Reserved Instance": ["Cloud Architecture"],
    "Savings Plan": ["Cloud Architecture"],

    # Infrastructure as Code / DevOps
    "Terraform": ["Infrastructure as Code", "DevOps"],
    "Ansible": ["Infrastructure as Code", "DevOps"],
    "Packer": ["Infrastructure as Code", "DevOps"],
    "Atlantis": ["Infrastructure as Code", "CI/CD"],
    "Kustomize": ["Infrastructure as Code", "DevOps"],
    "GitOps": ["Infrastructure as Code", "CI/CD"],
    "ArgoCD": ["CI/CD", "DevOps"],
    "CircleCI": ["CI/CD"],

    # Container orchestration / DevOps
    "Kubernetes": ["Container Orchestration", "DevOps", "Infrastructure Engineering"],
    "Docker": ["Container Orchestration", "DevOps"],
    "Rancher": ["Container Orchestration", "DevOps"],
    "DC/OS": ["Container Orchestration", "Infrastructure Engineering"],

    # Service Mesh
    "Istio": ["Service Mesh"],
    "Cilium": ["Service Mesh"],
    "Kuma": ["Service Mesh"],
    "Consul": ["Service Mesh", "Infrastructure Engineering"],

    # Security Engineering
    "Vault": ["Security Engineering"],
    "Okta": ["Security Engineering"],
    "OpenLDAP": ["Security Engineering"],
    "LDAP": ["Security Engineering"],
    "IPsec": ["Security Engineering"],
    "OpenVPN": ["Security Engineering"],
    "Kong": ["Security Engineering", "Microservices"],

    # Observability / Site Reliability Engineering
    "Kafka": ["Observability", "Microservices"],
    "Elastic Stack": ["Observability"],
    "Filebeat": ["Observability"],
    "Heartbeat": ["Observability"],
    "APM Server": ["Observability", "Site Reliability Engineering"],
    "Logstash": ["Observability"],
    "Elasticsearch": ["Observability"],
    "Kibana": ["Observability"],
    "Telegraf": ["Observability"],
    "InfluxDB": ["Observability"],
    "Grafana": ["Observability", "Site Reliability Engineering"],
    "CollectD": ["Observability"],

    # Microservices / Software Architecture
    "Node.js": ["Software Architecture", "Microservices"],
    "Koa": ["Software Architecture", "Microservices"],
    "REST API": ["Software Architecture"],
    "API": ["Software Architecture"],
    "microservices": ["Microservices", "Software Architecture"],
    "serverless": ["Software Architecture", "Cloud Architecture"],

    # Machine Learning
    "Machine Learning": ["Machine Learning"],
    "ML": ["Machine Learning"],
}


def extract_expertise(skills: list[str]) -> list[str]:
    """Derive professional expertise domains (e.g. 'DevOps', 'Cloud
    Architecture') from an already-extracted, canonicalized skills list.

    Order is deterministic: expertise domains appear in the order their
    first triggering skill first appears in `skills`, and each domain is
    reported once no matter how many of its trigger skills are present.
    """
    seen = set()
    results = []
    for skill in skills:
        for domain in SKILL_TO_EXPERTISE.get(skill, []):
            if domain not in seen:
                seen.add(domain)
                results.append(domain)
    return results


def _canonical_skill(value: str) -> str:
    key = re.sub(r"\s+", " ", value.strip()).lower()
    return SKILL_CANONICAL_MAP.get(key, value.strip())

def _skill_is_context_noise(ent, text: str) -> bool:
    """Reject taxonomy matches that are technically words but not skills."""
    value = re.sub(r"\s+", " ", ent.text.strip())
    lower = value.lower()

    if lower in SKILL_FALSE_POSITIVE_EXACT:
        return True

    # "Play" in this CV comes from "Google Play"; never expose it as a skill.
    if lower == "play":
        window = text[max(0, ent.start_char - 30):ent.end_char + 30].lower()
        if "google play" in window:
            return True

    # "Google" is useful only as part of "Google Workspace".
    if lower == "google":
        window = text[max(0, ent.start_char - 10):ent.end_char + 30].lower()
        if "google workspace" in window:
            return True

    # "Queue" here is part of "Dead Letter Queue", not a standalone technology.
    if lower == "queue":
        window = text[max(0, ent.start_char - 35):ent.end_char + 15].lower()
        if "dead letter queue" in window:
            return True

    # Never report a degree/domain phrase as a technical skill.
    if lower == "computer science":
        return True

    return False


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


def _line_boundaries(text: str) -> list[tuple[int, int, str]]:
    """Return (start_char, end_char, stripped_line_text) for every line in
    text, using the same character offsets spaCy entities use (ent.start_char).
    Used to expand a short EntityRuler match (e.g. just the word "University")
    out to the full line it appears on (e.g. the whole institution name),
    since a bare keyword match on its own throws away all the useful context
    around it."""
    lines = []
    offset = 0
    for raw_line in text.split("\n"):
        start = offset
        end = offset + len(raw_line)
        lines.append((start, end, raw_line.strip()))
        offset = end + 1  # +1 accounts for the newline character itself
    return lines


def _blank_line_blocks(text_slice: str) -> list[list[str]]:
    """Split a section's text into blocks of consecutive non-blank lines,
    separated by one or more blank lines. This depends on block-aware
    extraction (see extract_text_from_cv) preserving the PDF's real visual
    paragraph boundaries as blank lines -- without that, plain-text
    extraction collapses everything into one giant block with no way to
    tell where one CV entry ends and the next begins."""
    blocks = []
    current = []
    for raw_line in text_slice.split("\n"):
        stripped = raw_line.strip()
        if stripped:
            current.append(stripped)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    return blocks


_YEAR_ONLY_RE = re.compile(r"^(19|20)\d{2}$")


def _split_block_on_standalone_years(lines: list[str]) -> list[list[str]]:
    """If a block (lines with no blank-line separation between them, e.g.
    from a DOCX file, which has no visual 'block' concept the way a PDF
    does) contains multiple standalone year lines, treat each year -- and
    everything up to but not including the next standalone year -- as its
    own separate entry. This handles formats/CVs where distinct entries
    are packed together with no blank-line separator at all, but are still
    visually delimited by a repeating 'year, then description' pattern."""
    year_indexes = [i for i, line in enumerate(lines) if _YEAR_ONLY_RE.match(line)]
    if len(year_indexes) < 2:
        return [lines]

    sub_blocks = []
    if year_indexes[0] > 0:
        # Content before the first standalone year (rare) stays its own
        # leading block so it isn't silently dropped.
        sub_blocks.append(lines[:year_indexes[0]])
    for idx, start in enumerate(year_indexes):
        end = year_indexes[idx + 1] if idx + 1 < len(year_indexes) else len(lines)
        sub_blocks.append(lines[start:end])
    return sub_blocks


def _join_block_lines(lines: list[str]) -> str:
    """Join one entry's own lines into a single coherent string. A leading
    bare 4-digit year (e.g. a certification's issue year styled as its own
    line) is joined to the line right after it with a space -- "2023 AWS
    Certified ..." reads naturally, whereas "2023, AWS Certified..."
    doesn't. Every other line boundary is joined with a comma, since a
    résumé entry is usually a citation-style list (title, institution,
    location). Each line's own trailing comma/whitespace is stripped first
    so joining doesn't produce a doubled comma (e.g. a source line already
    ending in "Present," followed by our own comma-join)."""
    cleaned = [line.rstrip(", ") for line in lines]
    if len(cleaned) >= 2 and _YEAR_ONLY_RE.match(cleaned[0]):
        return ", ".join([f"{cleaned[0]} {cleaned[1]}"] + cleaned[2:])
    return ", ".join(cleaned)


def _is_date_or_location_tail(lines: list[str]) -> bool:
    """A short block (<=2 lines) whose content is essentially just a date
    range and/or a short location -- e.g. ['09/2022 - Present,',
    'Manouba'] -- is almost always a continuation of the entry immediately
    above it, not a new entry of its own. Some CV templates style the
    date/location line with different formatting than the title/
    institution line, which makes PDF block-extraction split them into
    separate visual blocks even though they belong to one logical entry."""
    if not lines or len(lines) > 2:
        return False
    joined = " ".join(lines)
    if not _DATE_RANGE_RE.search(joined):
        return False
    # Reject if the block also contains a long descriptive sentence -- a
    # genuine new entry that happens to start with its own date shouldn't
    # be silently swallowed into the previous one.
    return all(len(line.split()) <= 6 for line in lines)


def _group_section_into_entries(text_slice: str) -> list[str]:
    """Group a résumé section's raw lines into one string per logical
    entry:
      1. Split into blank-line-separated blocks (see _blank_line_blocks) --
         this is the primary signal, reflecting the PDF's real visual
         paragraph boundaries when block-aware extraction was used.
      2. Within any block that still contains multiple standalone-year
         lines (e.g. DOCX text, which has no blank-line/block concept at
         all), further split on that repeating pattern.
      3. Join each resulting entry's lines into one string, folding a
         trailing date/location-only block into the entry above it (see
         _is_date_or_location_tail) so a differently-styled date line
         doesn't get reported as its own fake entry.
    """
    entries = []
    for block_lines in _blank_line_blocks(text_slice):
        for lines in _split_block_on_standalone_years(block_lines):
            if entries and _is_date_or_location_tail(lines):
                entries[-1] = f"{entries[-1]}, {_join_block_lines(lines)}"
            else:
                entries.append(_join_block_lines(lines))

    return entries


def extract_education(doc, text: str) -> list[str]:
    """Return full education lines (institution + degree), not just the bare
    keyword the EntityRuler happened to match.

    The edu_ruler patterns are intentionally short/exact (e.g. the literal
    word "University", or the abbreviation "B.S.") so they reliably match
    across very different phrasings. But returning that bare match directly
    loses all context -- "University" on its own tells you nothing. Résumés
    reliably put one institution or degree per line, so expanding each match
    to its containing line recovers the actual useful information (e.g.
    "POSTECH (Pohang University of Science and Technology) Pohang, S.Korea").
    """
    lines = _line_boundaries(text)
    seen_lower = set()
    results = []

    for ent in doc.ents:
        if ent.label_ != "EDUCATION":
            continue
        for start, end, line_text in lines:
            if start <= ent.start_char < end:
                if line_text and line_text.lower() not in seen_lower:
                    seen_lower.add(line_text.lower())
                    results.append(line_text)
                break

    if results:
        return results

    # Fallback: some CVs contain an education section but use institution
    # names that do not contain our school keywords. Group the section's
    # lines into one coherent entry per logical block (see
    # _group_section_into_entries) instead of returning every raw line as
    # its own fragment.
    edu_matches = [
        m for m in _SECTION_HEADER_RE.finditer(text)
        if m.group(1).strip().lower() == "education"
    ]
    if edu_matches:
        start = edu_matches[0].end()
        end = len(text)
        for m in _SECTION_HEADER_RE.finditer(text, start):
            if m.start() > start:
                end = m.start()
                break

        for entry in _group_section_into_entries(text[start:end]):
            if entry and entry.lower() not in seen_lower:
                seen_lower.add(entry.lower())
                results.append(entry)

    return results


_CERTIFICATION_HEADER_WORDS = {"certificates", "certifications", "certificate", "certification"}


def extract_certifications(text: str) -> list[str]:
    """Return one coherent string per certification from the
    Certificates/Certifications section, if present. Uses the same
    block-based entry grouping as extract_education's fallback (see
    _group_section_into_entries) so a certification whose title and
    issuer/description span multiple PDF-extracted lines comes back as one
    entry rather than one fragment per line.
    """
    matches = [
        m for m in _SECTION_HEADER_RE.finditer(text)
        if m.group(1).strip().lower() in _CERTIFICATION_HEADER_WORDS
    ]
    if not matches:
        return []

    start = matches[0].end()
    end = len(text)
    for m in _SECTION_HEADER_RE.finditer(text, start):
        if m.start() > start:
            end = m.start()
            break

    seen_lower = set()
    results = []
    for entry in _group_section_into_entries(text[start:end]):
        if entry and entry.lower() not in seen_lower:
            seen_lower.add(entry.lower())
            results.append(entry)
    return results


def extract_skills(doc, text: str) -> list[str]:
    """Return normalized, deduplicated skills with obvious taxonomy noise removed.

    The Jobzilla taxonomy is intentionally broad. We therefore keep it as the
    discovery layer, but apply a quality gate before storing a skill:
      - reject known standalone false positives;
      - reject generic single-word taxonomy terms;
      - canonicalize aliases/casing;
      - deduplicate case-insensitively.
    """
    seen_lower = set()
    results = []

    for ent in doc.ents:
        if ent.label_ != "SKILL":
            continue

        if _skill_is_context_noise(ent, text):
            continue

        value = _canonical_skill(ent.text)

        if not value:
            continue

        if len(value.split()) == 1 and value.lower() in GENERIC_SKILL_BLOCKLIST:
            continue

        key = value.lower()
        if key in seen_lower:
            continue

        seen_lower.add(key)
        results.append(value)

    return results


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

# Generic single-word ORG fragments that carry no company-identifying
# signal on their own -- almost always a leftover piece of a job title
# ("Software Architect" -> "Software") or a stray section word, not an
# actual employer name.
GENERIC_ORG_BLOCKLIST = {
    "software", "service", "services", "team", "solutions", "group",
    "technology", "technologies",
}

# Specific products/tools that spaCy's NER reliably mis-tags as ORG because
# they're capitalized proper nouns, but which are never themselves an
# employer -- e.g. "...email, SMS, Kakaotalk and Slack notification..."
# reads exactly like a list of company names to a general-purpose NER
# model. Same curation pattern already used for CUSTOM_TECH_SKILLS above;
# this list is expected to grow as new real-world false positives surface.
KNOWN_NON_COMPANY_PRODUCTS = {"kakaotalk", "slack", "whatsapp", "telegram"}

# If an extracted "company" contains one of these role/description words
# AND has no business-entity marker (see BUSINESS_ENTITY_MARKERS), it's
# almost certainly a job title or duty description that NER mis-tagged as
# an org, not an actual employer -- e.g. "Reliability Engineer &
# Infrastructure Team Lead" or "Compulsory Military Service".
JOB_TITLE_WORDS = {
    "engineer", "architect", "lead", "manager", "director", "administrator",
    "researcher", "specialist", "consultant", "developer", "military",
}

BUSINESS_ENTITY_MARKERS = {
    "inc", "corp", "corporation", "co", "ltd", "llc", "company",
    "companies", "group", "technologies", "systems", "solutions", "holdings",
}


def _looks_like_job_title_not_company(text: str) -> bool:
    words = re.sub(r"[.,&]", " ", text.lower()).split()
    has_business_marker = any(w in BUSINESS_ENTITY_MARKERS for w in words)
    if has_business_marker:
        return False
    return any(w in JOB_TITLE_WORDS for w in words)


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
    # Generic single-word ORG fragment ("Software" peeled off "Software
    # Architect") -- see GENERIC_ORG_BLOCKLIST above.
    if len(words) == 1 and text.lower() in GENERIC_ORG_BLOCKLIST:
        return True
    # Known product/tool names that NER reliably mis-tags as companies.
    if text.lower() in KNOWN_NON_COMPANY_PRODUCTS:
        return True

    return False

# Resume work-history entries are much more reliable than unrestricted ORG NER:
# in the supplied CV every employer line is immediately followed by a role/date
# line. This avoids turning "Reliability Engineer & Infrastructure Team Lead",
# "Compulsory Military Service", "Kakaotalk", etc. into companies.
#
# Two date formats are recognized: month-name ("Jun. 2023") and numeric
# ("06/2023") -- different CV templates use different conventions, and a
# regex built around only one silently fails to detect any date line at all
# for CVs using the other (which then breaks every downstream heuristic
# anchored on finding the date line, e.g. company extraction).
_MONTH_NAME_DATE = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{4}"
_NUMERIC_DATE = r"\d{1,2}/\d{4}"

_DATE_RANGE_RE = re.compile(
    r"\b(?:" + _MONTH_NAME_DATE + r"|" + _NUMERIC_DATE + r")\s*(?:-|–|—|to)\s*"
    r"(?:" + _MONTH_NAME_DATE + r"|" + _NUMERIC_DATE + r"|Present|Current)\b",
    re.IGNORECASE,
)

def _nonempty_lines_with_offsets(text: str, char_range: tuple[int, int]) -> list[tuple[int, int, str]]:
    start, end = char_range
    result = []

    for raw_start, raw_end, line_text in _line_boundaries(text):
        if raw_end <= start or raw_start >= end:
            continue
        stripped = line_text.strip()
        if stripped:
            result.append((raw_start, raw_end, stripped))

    return result

def _strip_location_from_company_line(
    line: str,
    line_start: int,
    doc,
) -> str:
    """Remove trailing GPE/location spans while preserving the employer name."""
    absolute_end = line_start + len(line)

    gpes = [
        ent for ent in doc.ents
        if ent.label_ in {"GPE", "LOC"}
        and line_start <= ent.start_char < absolute_end
        and ent.end_char <= absolute_end
    ]

    if gpes:
        # Only remove a GPE if it occurs near the end of the employer line.
        last = max(gpes, key=lambda e: e.end_char)
        if last.end_char >= line_start + int(len(line) * 0.55):
            line = line[:last.start_char - line_start].rstrip(" ,|-")

    # Fallback for common "City, Country" suffixes when NER does not tag the
    # location. It is deliberately conservative and only removes the suffix
    # after a company-like prefix.
    line = re.sub(
        r"\s+(?:Seoul|New York|San Francisco|London|Paris|"
        r"Toronto|Singapore|Tokyo|Pohang),\s*"
        r"(?:S\.Korea|South Korea|Republic of Korea|U\.S\.A\.|USA|"
        r"United States|UK|United Kingdom|Canada|Japan)\s*$",
        "",
        line,
        flags=re.IGNORECASE,
    )

    return line.strip(" ,|-")

def _looks_like_company_candidate(line: str) -> bool:
    """Reject obvious role/title lines when layout detection produces a candidate."""
    if not line or len(line) > 140:
        return False

    if line.startswith(("•", "-", "–", "—")):
        return False

    if _looks_like_noise(line):
        return False

    if _looks_like_job_title_not_company(line):
        # A real company can contain these words, but standalone role-shaped
        # lines without a business marker are overwhelmingly job titles.
        return False

    return True

_KNOWN_LOCATION_COUNTRIES = (
    r"S\.Korea|South Korea|Republic of Korea|U\.S\.A\.|USA|"
    r"United States|UK|United Kingdom|Canada|Japan|Germany|France|"
    r"Australia|India|China|Ireland|Spain|Italy|Netherlands|Singapore"
)

# Matches a standalone "City, ST" (US-style 2-letter state) or "City,
# Country" line. Deliberately general rather than a hardcoded city list --
# spaCy's GPE/LOC entities can't be trusted as the sole fallback here (e.g.
# it tags "Austin" as PERSON and "TX" as ORG in short address-only lines,
# not GPE/LOC at all), so a location-shaped text pattern catches what NER
# misses.
_LOCATION_ONLY_RE = re.compile(
    r"^\s*[A-Za-z][A-Za-z.\s'\-]*,\s*"
    r"(?:[A-Z]{2}|" + _KNOWN_LOCATION_COUNTRIES + r")\s*$"
)


def _line_is_location_only(line: str, line_start: int, line_end: int, doc) -> bool:
    """Detect a résumé line that is nothing but a city/country (e.g. 'Seoul,
    S.Korea' or 'Austin, TX' on its own line, separate from the employer
    name above it and the role title below it). Needed because many résumé
    layouts put company, location, role, and date on four separate lines
    rather than the two the original layout heuristic assumed -- without
    skipping the location line, the heuristic reads the role title (or the
    location itself) as the employer name."""
    if not line:
        return False

    if _LOCATION_ONLY_RE.match(line):
        return True

    # Fallback: if a GPE/LOC entity covers most of the line's characters,
    # treat it as a location-only line even where the text pattern above
    # doesn't match (e.g. a country name spelled out that isn't in the
    # known list). This is a genuine best-effort fallback, not a
    # guarantee -- spaCy's generic NER can mislabel short address-only
    # lines (city names read as PERSON, state codes read as ORG), so the
    # text pattern above is the more reliable signal when it applies.
    ents = [
        e for e in doc.ents
        if e.label_ in {"GPE", "LOC"}
        and line_start <= e.start_char < line_end
        and e.end_char <= line_end
    ]
    if not ents:
        return False
    covered = sum(e.end_char - e.start_char for e in ents)
    return covered >= 0.6 * max(len(line), 1)


def extract_companies_from_experience(
    doc,
    text: str,
    experience_span: tuple[int, int] | None,
) -> list[str]:
    """Extract employer names from the Work Experience section.

    Primary strategy:
      company line -> role/date line

    Fallback:
      ORG NER restricted to the Work Experience section.
    """
    seen = set()
    results = []

    if experience_span:
        lines = _nonempty_lines_with_offsets(text, experience_span)

        # Look for a role/date line. The preceding non-empty line is the
        # employer in the common two-line resume layout.
        for i, (start, end, line) in enumerate(lines):
            if not _DATE_RANGE_RE.search(line):
                continue

            if i == 0:
                continue

            # Walk backward past a role/title line and/or a standalone
            # location line to find the actual employer line. Layouts vary:
            # some put company+location on one line and role+date on the
            # next (2-line); this CV puts company, location, role, and date
            # each on their own line (4-line). A fixed "one line back"
            # assumption only handles the former. Bounded to 3 lines back so
            # a malformed layout can't walk arbitrarily far and grab the
            # wrong text.
            j = i - 1
            skipped_role = False
            while j >= 0 and (i - j) <= 3:
                cand_start, cand_end, cand_line = lines[j]
                if not skipped_role and _looks_like_job_title_not_company(cand_line):
                    skipped_role = True
                    j -= 1
                    continue
                if _line_is_location_only(cand_line, cand_start, cand_end, doc):
                    j -= 1
                    continue
                break

            if j < 0 or (i - j) > 3:
                continue

            previous_start, _, previous_line = lines[j]

            # If the date is on the employer line itself, prefer ORG NER
            # rather than treating the whole role/date line as the company.
            if _looks_like_job_title_not_company(previous_line):
                continue

            candidate = _strip_location_from_company_line(
                previous_line,
                previous_start,
                doc,
            )

            if not _looks_like_company_candidate(candidate):
                continue

            key = candidate.lower()
            if key not in seen:
                seen.add(key)
                results.append(candidate)

        # If layout extraction found employers, trust it. This prevents the
        # general NER model from adding certificates, community groups, tools,
        # job titles, and sentence fragments.
        if results:
            return results

    # Fallback for unconventional CV layouts.
    return extract_entities(
        doc,
        ("ORG",),
        char_range=experience_span,
        filter_job_titles=True,
    )


def extract_entities(
    doc,
    labels: tuple[str, ...],
    char_range: tuple[int, int] | None = None,
    filter_job_titles: bool = False,
) -> list[str]:
    """Extract entities with the given labels, optionally restricted to a
    character-offset range within the original text (see char_range param
    on parse_cv -- used to keep 'companies' scoped to the Work Experience
    section only, see _find_experience_section below).

    filter_job_titles: when True (used for the companies list specifically),
    also drops entities that look like job titles/duty descriptions rather
    than actual employer names -- see _looks_like_job_title_not_company.
    """
    seen_lower = set()
    results = []
    for ent in doc.ents:
        if ent.label_ not in labels:
            continue
        if char_range and not (char_range[0] <= ent.start_char < char_range[1]):
            continue
        value = ent.text.strip()
        if not value or value.lower() in seen_lower:
            continue
        if _looks_like_noise(value):
            continue
        if filter_job_titles and _looks_like_job_title_not_company(value):
            continue
        seen_lower.add(value.lower())
        results.append(value)
    return results


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
    skills = extract_skills(doc, text)

    return {
        "name": pick_name(doc, text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "years_of_experience": extract_years_of_experience(text),
        "expertise": extract_expertise(skills),
        "skills": skills,
        "education": extract_education(doc, text),
        "certifications": extract_certifications(text),
        "companies": extract_companies_from_experience(
            doc, text, experience_span
        ),
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