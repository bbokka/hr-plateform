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
    """Combine structured skills with raw CV text for a stronger embedding.
    Prepending skills gives the model a concentrated signal to anchor on,
    while the raw text still carries context, seniority, and domain nuance.
    """


    skills = cv_parsed_data.get("skills", []) if cv_parsed_data else []
    skills_line = f"Skills: {', '.join(skills)}\n\n" if skills else ""
    return f"{skills_line}{cv_raw_text or ''}"