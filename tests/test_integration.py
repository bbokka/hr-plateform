"""Integration test for the async CV upload pipeline.

Unlike the other API tests, this one requires a REAL Celery worker to be
running and consuming from the SAME database this test writes to. It is
designed to run in CI, where both DATABASE_URL and TEST_DATABASE_URL point
at the same throwaway Postgres instance, and a worker process is started
in the background before pytest runs.

Locally, this test will simply hang until timeout unless you deliberately
run a worker pointed at your test DB -- that's expected and fine; treat
this as a CI-primary test.

The CV used here is generated on the fly (not a committed fixture file),
so no personal/sample data needs to live in the repo.
"""
import time

import pymupdf
import pytest

POLL_INTERVAL_SECONDS = 1
MAX_WAIT_SECONDS = 30

SYNTHETIC_CV_TEXT = """Jordan Reilly
Software Engineer
jordan.reilly.testfixture@example.com
(202) 555-0143

Work Experience

Backend Engineer, Northwind Systems
Built REST APIs with Python and FastAPI. Deployed on AWS. 4 years experience.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL

Education
Bachelor of Science, State University
"""


@pytest.fixture
def synthetic_cv_pdf(tmp_path):
    """Generate a minimal real PDF with known text content, so this test
    never depends on a committed sample file."""
    pdf_path = tmp_path / "synthetic_cv.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), SYNTHETIC_CV_TEXT, fontsize=11)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_cv_upload_is_processed_asynchronously(client, synthetic_cv_pdf):
    """Full round trip: upload a CV, confirm the endpoint returns
    immediately with a 'pending' status, then poll until the background
    worker finishes and confirm the parsed data + embedding landed."""

    candidate = client.post("/candidates", json={
        "full_name": "Jordan Reilly",
        "email": "jordan.reilly.integration.test@example.com",
    }).json()
    candidate_id = candidate["id"]

    with open(synthetic_cv_pdf, "rb") as f:
        upload_response = client.post(
            f"/candidates/{candidate_id}/cv",
            files={"file": ("synthetic_cv.pdf", f, "application/pdf")},
        )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data["processing_status"] == "pending"
    assert upload_data["candidate_id"] == candidate_id

    final_status = None
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        check = client.get(f"/candidates/{candidate_id}")
        final_status = check.json()["processing_status"]
        if final_status in ("completed", "failed"):
            break
        time.sleep(POLL_INTERVAL_SECONDS)

    assert final_status == "completed", (
        f"Expected candidate to reach 'completed' within {MAX_WAIT_SECONDS}s, "
        f"got '{final_status}'. Is a Celery worker running against the same DB?"
    )

    candidate_after = client.get(f"/candidates/{candidate_id}").json()
    assert candidate_after["cv_parsed_data"] is not None
    assert candidate_after["cv_parsed_data"].get("name")
    assert "python" in [s.lower() for s in candidate_after["cv_parsed_data"].get("skills", [])]
    assert candidate_after["embedding"] is not None
    assert len(candidate_after["embedding"]) == 384