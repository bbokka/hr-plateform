"""Stage 4: turn text into vectors for semantic similarity search.

Uses sentence-transformers' all-MiniLM-L6-v2 — a small, fast, free
pretrained model producing 384-dimensional embeddings, matching the
Vector(384) columns on Job and Candidate.
"""
from sentence_transformers import SentenceTransformer

_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """Convert text into a 384-dim embedding vector."""
    if not text or not text.strip():
        return None
    vector = _MODEL.encode(text.strip())
    return vector.tolist()


def build_candidate_embedding_text(cv_raw_text: str, cv_parsed_data: dict) -> str:
    """Combine structured fields with raw CV text for a stronger embedding.

    Expertise, technical skills, and certifications are each prepended as
    their own labeled line (in that order -- broad domain signal first,
    concrete tools second, credentials third) to give the model concentrated,
    distinctly-tagged anchors to match on, while the raw text still carries
    context, seniority, and domain nuance. Any field that's empty/missing is
    simply omitted rather than emitted as an empty line.
    """
    cv_parsed_data = cv_parsed_data or {}

    expertise = cv_parsed_data.get("expertise", [])
    skills = cv_parsed_data.get("skills", [])
    certifications = cv_parsed_data.get("certifications", [])

    prefix_lines = []
    if expertise:
        prefix_lines.append(f"Expertise: {', '.join(expertise)}")
    if skills:
        prefix_lines.append(f"Skills: {', '.join(skills)}")
    if certifications:
        prefix_lines.append(f"Certifications: {', '.join(certifications)}")

    prefix = "\n".join(prefix_lines)
    prefix = f"{prefix}\n\n" if prefix else ""
    return f"{prefix}{cv_raw_text or ''}"