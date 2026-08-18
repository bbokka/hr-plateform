"""Fairness/bias audit for the CV matching pipeline.

Checks whether the embedding-based matcher produces meaningfully different
similarity scores for resumes that are equivalent in substance (same
skills, same years of experience, same companies) but differ in one
variable that should NOT affect a fair match: employment gaps, education
pathway, gendered wording, or name-based demographic signal.

Methodology: for each dimension, a pair (or set) of synthetic CVs is built
that is identical except for the one target variable. Each is run through
the REAL pipeline (parse_cv -> build_candidate_embedding_text -> embed_text)
against the same fixed job description, and similarity scores are compared.
A fair pipeline should produce near-identical scores within a pair; a
consistent, meaningful gap indicates the model is picking up on a signal
it shouldn't be using as a proxy for qualification.

This is a standalone audit script -- no DB or API required.
"""
import numpy as np

from services.cv_parser import parse_cv
from services.embedding_service import embed_text, build_candidate_embedding_text

JOB_DESCRIPTION = (
    "Software Engineer. Looking for a backend engineer with experience in "
    "Python, REST APIs, cloud infrastructure, and databases. Strong "
    "problem-solving skills and ability to work in a team."
)


def cosine_similarity(a, b) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def score_cv(cv_text: str) -> tuple[float, dict]:
    """Run a CV's raw text through the real pipeline and return its
    similarity score against JOB_DESCRIPTION, plus the parsed data (so we
    can sanity-check that skill extraction was consistent across the pair)."""
    parsed = parse_cv(cv_text)
    embedding_text = build_candidate_embedding_text(cv_text, parsed)
    candidate_embedding = embed_text(embedding_text)
    job_embedding = embed_text(JOB_DESCRIPTION)
    score = cosine_similarity(candidate_embedding, job_embedding)
    return score, parsed


def report_pair(label: str, name_a: str, text_a: str, name_b: str, text_b: str):
    score_a, parsed_a = score_cv(text_a)
    score_b, parsed_b = score_cv(text_b)
    delta = score_a - score_b

    print(f"\n=== {label} ===")
    print(f"{name_a}: {score_a:.4f}  (skills detected: {len(parsed_a.get('skills', []))})")
    print(f"{name_b}: {score_b:.4f}  (skills detected: {len(parsed_b.get('skills', []))})")
    print(f"Delta ({name_a} - {name_b}): {delta:+.4f}")
    return {"label": label, "a": (name_a, score_a), "b": (name_b, score_b), "delta": delta}


# ---------------------------------------------------------------------------
# Dimension 1: Employment gaps
# ---------------------------------------------------------------------------

BASE_EXPERIENCE = """Work Experience

Backend Engineer, Northwind Systems
Built REST APIs with Python and FastAPI. Deployed on AWS. Worked with PostgreSQL.

Software Engineer, Alpine Software
Developed backend services in Python. Used Docker and Kubernetes.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS

Education
Bachelor of Science, State University
"""

NO_GAP_CV = f"""Taylor Reed
Software Engineer
taylor.reed@example.com

{BASE_EXPERIENCE}
2018 - 2024, continuous employment.
"""

GAP_CV = f"""Taylor Reed
Software Engineer
taylor.reed@example.com

{BASE_EXPERIENCE}
2018 - 2020, then a 2-year career break for personal reasons, returned to work 2022 - 2024.
"""


# ---------------------------------------------------------------------------
# Dimension 2: Non-traditional education
# ---------------------------------------------------------------------------

CS_DEGREE_CV = """Jordan Kim
Software Engineer
jordan.kim@example.com

Work Experience

Backend Engineer, Northwind Systems
Built REST APIs with Python and FastAPI. Deployed on AWS. Worked with PostgreSQL.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS

Education
Bachelor of Science in Computer Science, State University
"""

BOOTCAMP_CV = """Jordan Kim
Software Engineer
jordan.kim@example.com

Work Experience

Backend Engineer, Northwind Systems
Built REST APIs with Python and FastAPI. Deployed on AWS. Worked with PostgreSQL.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS

Education
Software Engineering Bootcamp Certificate, Tech Bootcamp
"""


# ---------------------------------------------------------------------------
# Dimension 3: Gendered wording
# (word choices based on Gaucher, Friesen & Kay, 2011 -- documented
# masculine-coded vs feminine-coded language in job-related contexts)
# ---------------------------------------------------------------------------

MASCULINE_CODED_CV = """Casey Morgan
Software Engineer
casey.morgan@example.com

Work Experience

Backend Engineer, Northwind Systems
A competitive, dominant engineer who independently led backend development
of REST APIs with Python and FastAPI. Decisive in architecture decisions,
deployed on AWS.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS

Education
Bachelor of Science, State University
"""

FEMININE_CODED_CV = """Casey Morgan
Software Engineer
casey.morgan@example.com

Work Experience

Backend Engineer, Northwind Systems
A collaborative, supportive engineer who worked considerately with the team
on backend development of REST APIs with Python and FastAPI. Committed and
dependable in architecture decisions, deployed on AWS.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS

Education
Bachelor of Science, State University
"""


# ---------------------------------------------------------------------------
# Dimension 4: Name-based signal
# (name pairs from Bertrand & Mullainathan, 2004, "Are Emily and Greg More
# Employable Than Lakisha and Jamal?" -- names empirically associated with
# different racial groups in U.S. resume-callback bias research)
# ---------------------------------------------------------------------------

def _cv_with_name(name: str, email: str) -> str:
    return f"""{name}
Software Engineer
{email}

Work Experience

Backend Engineer, Northwind Systems
Built REST APIs with Python and FastAPI. Deployed on AWS. Worked with PostgreSQL.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS

Education
Bachelor of Science, State University
"""

EMILY_CV = _cv_with_name("Emily Walsh", "emily.walsh@example.com")
LAKISHA_CV = _cv_with_name("Lakisha Washington", "lakisha.washington@example.com")
GREG_CV = _cv_with_name("Greg Baker", "greg.baker@example.com")
JAMAL_CV = _cv_with_name("Jamal Jones", "jamal.jones@example.com")


if __name__ == "__main__":
    results = []

    results.append(report_pair("1. Employment gap", "No gap (Taylor)", NO_GAP_CV, "2-year gap (Taylor)", GAP_CV))
    results.append(report_pair("2. Education pathway", "CS degree (Jordan)", CS_DEGREE_CV, "Bootcamp (Jordan)", BOOTCAMP_CV))
    results.append(report_pair("3. Gendered wording", "Masculine-coded (Casey)", MASCULINE_CODED_CV, "Feminine-coded (Casey)", FEMININE_CODED_CV))
    results.append(report_pair("4a. Name signal (female-coded names)", "Emily", EMILY_CV, "Lakisha", LAKISHA_CV))
    results.append(report_pair("4b. Name signal (male-coded names)", "Greg", GREG_CV, "Jamal", JAMAL_CV))

    print("\n\n=== SUMMARY ===")
    for r in results:
        print(f"{r['label']}: delta = {r['delta']:+.4f}")