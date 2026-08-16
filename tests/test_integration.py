"""Integration test for the async CV upload pipeline.

Unlike the other API tests, this one requires a REAL Celery worker to be
running and consuming from the SAME database this test writes to. It is
designed to run in CI, where both DATABASE_URL and TEST_DATABASE_URL point
at the same throwaway Postgres instance, and a worker process is started
in the background before pytest runs.

Locally, this test will simply hang until timeout unless you deliberately
run a worker pointed at your test DB — that's expected and fine; treat
this as a CI-primary test.
"""
import time
from pathlib import Path

SAMPLE_CV_PATH = Path(__file__).resolve().parent.parent / "sample_cvs" / "Alex_Morgan_Software_Engineer_CV.pdf"

POLL_INTERVAL_SECONDS = 1
MAX_WAIT_SECONDS = 30


def test_cv_upload_is_processed_asynchronously(client):
    """Full round trip: upload a real CV, confirm the endpoint returns
    immediately with a 'pending' status, then poll until the background
    worker finishes and confirm the parsed data + embedding landed."""

    candidate = client.post("/candidates", json={
        "full_name": "Alex Morgan",
        "email": "alex.morgan.integration.test@example.com",
    }).json()
    candidate_id = candidate["id"]

    with open(SAMPLE_CV_PATH, "rb") as f:
        upload_response = client.post(
            f"/candidates/{candidate_id}/cv",
            files={"file": ("Alex_Morgan_Software_Engineer_CV.pdf", f, "application/pdf")},
        )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data["processing_status"] == "pending"
    assert upload_data["candidate_id"] == candidate_id

    # Poll for the background worker to finish, instead of asserting on
    # immediate state -- the whole point of this pipeline is that
    # processing happens out-of-band, so the test has to wait for it.
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
    assert candidate_after["embedding"] is not None
    assert len(candidate_after["embedding"]) == 384