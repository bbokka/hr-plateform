"""Tests for the semantic matching logic specifically -- i.e. does
GET /jobs/{job_id}/matches actually rank candidates by relevance, not just
respond without crashing.

Candidate embeddings are set directly via the DB session (using the real
embed_text() function) rather than going through the full CV upload +
Celery pipeline. This keeps these tests fast and independent of a running
worker, while still exercising the real embedding model and real pgvector
cosine_distance query -- the two things whose correctness actually matters
here.
"""
from models import Candidate
from services.embedding_service import embed_text

DEVOPS_JOB_DESCRIPTION = (
    "Senior DevOps Engineer. Kubernetes, Terraform, AWS, Docker, CI/CD "
    "pipelines, infrastructure as code, monitoring and observability."
)

DEVOPS_CANDIDATE_TEXT = (
    "Experienced DevOps engineer. 5 years managing Kubernetes clusters, "
    "writing Terraform modules, deploying on AWS, building CI/CD pipelines "
    "with Docker and GitHub Actions."
)

MARKETING_CANDIDATE_TEXT = (
    "Marketing manager with 6 years of experience running social media "
    "campaigns, brand strategy, content marketing, and email newsletters "
    "for consumer products."
)


def _create_candidate_with_embedding(db_session, full_name, email, raw_text):
    candidate = Candidate(
        full_name=full_name,
        email=email,
        cv_raw_text=raw_text,
        cv_parsed_data={},
        embedding=embed_text(raw_text),
        processing_status="completed",
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def test_matches_ranks_relevant_candidate_above_irrelevant(client, db_session):
    """The core matching claim: a candidate whose background genuinely
    overlaps with the job should score higher than one who doesn't."""
    job = client.post("/jobs", json={
        "title": "Senior DevOps Engineer",
        "description": DEVOPS_JOB_DESCRIPTION,
    }).json()

    _create_candidate_with_embedding(
        db_session, "DevOps Dana", "devops.dana@example.com", DEVOPS_CANDIDATE_TEXT
    )
    _create_candidate_with_embedding(
        db_session, "Marketing Mo", "marketing.mo@example.com", MARKETING_CANDIDATE_TEXT
    )

    response = client.get(f"/jobs/{job['id']}/matches")
    assert response.status_code == 200

    results = response.json()
    assert len(results) == 2

    scores_by_name = {r["full_name"]: r["similarity_score"] for r in results}
    assert scores_by_name["DevOps Dana"] > scores_by_name["Marketing Mo"]

    # Results should already come back ordered by relevance (highest first).
    assert results[0]["full_name"] == "DevOps Dana"


def test_matches_similarity_scores_are_in_a_sane_range(client, db_session):
    """Cosine similarity should land in a sane, bounded range -- not NaN,
    not wildly outside [-1, 1], and the exact-match case should score
    close to 1.0."""
    job = client.post("/jobs", json={
        "title": "Senior DevOps Engineer",
        "description": DEVOPS_JOB_DESCRIPTION,
    }).json()

    # A candidate whose CV text is identical to the job description should
    # score very close to a perfect match.
    _create_candidate_with_embedding(
        db_session, "Exact Match", "exact.match@example.com", DEVOPS_JOB_DESCRIPTION
    )

    results = client.get(f"/jobs/{job['id']}/matches").json()
    assert len(results) == 1
    score = results[0]["similarity_score"]
    assert -1.0 <= score <= 1.0
    assert score > 0.95


def test_matches_excludes_candidates_without_an_embedding(client, db_session):
    """A candidate who hasn't been processed yet (no embedding) should
    never show up in match results -- there's nothing to rank them by."""
    job = client.post("/jobs", json={
        "title": "Senior DevOps Engineer",
        "description": DEVOPS_JOB_DESCRIPTION,
    }).json()

    unprocessed = Candidate(
        full_name="Unprocessed Candidate",
        email="unprocessed@example.com",
        processing_status="pending",
        embedding=None,
    )
    db_session.add(unprocessed)
    db_session.commit()

    results = client.get(f"/jobs/{job['id']}/matches").json()
    assert results == []


def test_matches_respects_the_limit_parameter(client, db_session):
    """?limit=N should cap the number of results returned, keeping the
    highest-ranked candidates."""
    job = client.post("/jobs", json={
        "title": "Senior DevOps Engineer",
        "description": DEVOPS_JOB_DESCRIPTION,
    }).json()

    for i in range(5):
        _create_candidate_with_embedding(
            db_session, f"Candidate {i}", f"candidate{i}@example.com", DEVOPS_CANDIDATE_TEXT
        )

    response = client.get(f"/jobs/{job['id']}/matches", params={"limit": 2})
    assert len(response.json()) == 2


def test_matches_returns_empty_list_when_no_candidates_exist(client):
    job = client.post("/jobs", json={
        "title": "Senior DevOps Engineer",
        "description": DEVOPS_JOB_DESCRIPTION,
    }).json()

    response = client.get(f"/jobs/{job['id']}/matches")
    assert response.status_code == 200
    assert response.json() == []