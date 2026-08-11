"""Seed the running API with demo jobs + candidates for frontend testing.

Usage:
    1. Make sure your FastAPI server is running (uvicorn main:app --reload)
    2. Drop a few real CV files (PDF/DOCX) into a folder, e.g. sample_cvs/
    3. Run: python scripts/seed_demo_data.py

This hits the real running API over HTTP — same code path a real user would
trigger — so it exercises extraction, parsing, and embedding end-to-end,
just without manual clicking.
"""
import sys
from pathlib import Path

import requests

API_BASE = "http://localhost:8000"

DEMO_JOBS = [
    {
        "title": "Senior DevOps Engineer",
        "description": (
            "Looking for a DevOps engineer with strong Kubernetes, Terraform, "
            "and AWS experience to lead infrastructure scaling and reliability."
        ),
    },
    {
        "title": "Backend Python Developer",
        "description": (
            "Seeking a backend developer with FastAPI, PostgreSQL, and REST API "
            "design experience. Docker and CI/CD knowledge a plus."
        ),
    },
    {
        "title": "Marketing Manager",
        "description": (
            "We need a marketing manager to lead brand strategy, social media "
            "campaigns, and content marketing initiatives."
        ),
    },
    {
        "title": "Frontend React Developer",
        "description": (
            "Frontend developer with React, TypeScript, and Tailwind CSS "
            "experience to build modern, accessible web interfaces."
        ),
    },
]

DEMO_CANDIDATES = [
    {"full_name": "Alice Martin", "email": "alice.martin@example.com"},
    {"full_name": "Byungjin Park", "email": "byungjin.park@example.com"},
    {"full_name": "Carlos Ruiz", "email": "carlos.ruiz@example.com"},
]

# Folder containing real CV files to upload — matched to DEMO_CANDIDATES by index.
# If there are fewer CVs than candidates, remaining candidates are created
# without a CV (useful for testing the "no CV yet" empty state too).
CV_FOLDER = Path("sample_cvs")


def seed_jobs():
    print("Seeding jobs...")
    for job in DEMO_JOBS:
        resp = requests.post(f"{API_BASE}/jobs", json=job)
        if resp.status_code == 200:
            print(f"  Created job: {job['title']} (id={resp.json()['id']})")
        else:
            print(f"  FAILED to create job '{job['title']}': {resp.status_code} {resp.text}")


def seed_candidates():
    print("\nSeeding candidates...")
    cv_files = sorted(CV_FOLDER.glob("*")) if CV_FOLDER.exists() else []

    for i, candidate in enumerate(DEMO_CANDIDATES):
        resp = requests.post(f"{API_BASE}/candidates", json=candidate)
        if resp.status_code != 200:
            print(f"  FAILED to create candidate '{candidate['full_name']}': "
                  f"{resp.status_code} {resp.text}")
            continue

        candidate_id = resp.json()["id"]
        print(f"  Created candidate: {candidate['full_name']} (id={candidate_id})")

        if i < len(cv_files):
            cv_path = cv_files[i]
            with open(cv_path, "rb") as f:
                upload_resp = requests.post(
                    f"{API_BASE}/candidates/{candidate_id}/cv",
                    files={"file": (cv_path.name, f)},
                )
            if upload_resp.status_code == 200:
                print(f"    Uploaded CV: {cv_path.name}")
            else:
                print(f"    FAILED to upload CV for {candidate['full_name']}: "
                      f"{upload_resp.status_code} {upload_resp.text}")
        else:
            print(f"    (no CV file available for this candidate — skipped)")


def check_server():
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=3)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


if __name__ == "__main__":
    if not check_server():
        print(f"ERROR: could not reach {API_BASE}. Is `uvicorn main:app --reload` running?")
        sys.exit(1)

    if not CV_FOLDER.exists():
        print(f"NOTE: '{CV_FOLDER}/' folder not found — candidates will be created "
              f"without CVs. Create this folder and add a few PDF/DOCX files to "
              f"also test the upload/parsing pipeline.\n")

    seed_jobs()
    seed_candidates()
    print("\nDone. Check the frontend or /docs to see the seeded data.")