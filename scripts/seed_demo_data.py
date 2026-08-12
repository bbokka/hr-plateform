"""Seed the running API with demo jobs + candidates for frontend testing.

Usage:
    1. Make sure your FastAPI server is running (uvicorn main:app --reload)
    2. Place CV files in sample_cvs/ (already matched below by filename)
    3. Run: python scripts/seed_demo_data.py

This hits the real running API over HTTP -- same code path a real user would
trigger -- so it exercises extraction, parsing, and embedding end-to-end,
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
    {
        "title": "Data Scientist",
        "description": (
            "Data scientist role focused on machine learning, NLP, and "
            "predictive modeling using Python, PyTorch, and SQL."
        ),
    },
    {
        "title": "UX/UI Designer",
        "description": (
            "UX/UI designer with strong Figma skills, experience running "
            "user research, wireframing, and building design systems."
        ),
    },
]

# Explicit filename -> candidate mapping. This is deliberate instead of
# relying on alphabetical folder order, which previously caused a mismatch
# (David Chen's CV silently landed on the "Byungjin Park" candidate record
# because it happened to sort second in the folder).
CV_FOLDER = Path("sample_cvs")

CANDIDATE_CV_MAP = [
    {"full_name": "Alex Morgan", "email": "alex.morgan@example.com",
     "cv_file": "Alex_Morgan_Software_Engineer_CV.pdf"},
    {"full_name": "David Chen", "email": "david.chen.ai@example.com",
     "cv_file": "David_Chen_Data_Scientist_CV.pdf"},
    {"full_name": "Elena Rostova", "email": "elena.rostova.design@example.com",
     "cv_file": "Elena_Rostova_UX_UI_Designer_CV.pdf"},
    {"full_name": "Byungjin Park", "email": "byungjin.park@example.com",
     "cv_file": "resume.pdf"},
    {"full_name": "Sarah Jenkins", "email": "sarah.jenkins@example.com",
     "cv_file": "Sarah_Jenkins_Marketing_Director_CV.pdf"},
    {"full_name": "aziz BenAmor", "email": "AzizBenAmor@example.com",
     "cv_file": "test_CV.pdf"},
]


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

    for entry in CANDIDATE_CV_MAP:
        resp = requests.post(f"{API_BASE}/candidates", json={
            "full_name": entry["full_name"],
            "email": entry["email"],
        })
        if resp.status_code != 200:
            print(f"  FAILED to create candidate '{entry['full_name']}': "
                  f"{resp.status_code} {resp.text}")
            continue

        candidate_id = resp.json()["id"]
        print(f"  Created candidate: {entry['full_name']} (id={candidate_id})")

        cv_path = CV_FOLDER / entry["cv_file"]
        if not cv_path.exists():
            print(f"    WARNING: expected CV file not found: {cv_path} — skipped")
            continue

        with open(cv_path, "rb") as f:
            upload_resp = requests.post(
                f"{API_BASE}/candidates/{candidate_id}/cv",
                files={"file": (cv_path.name, f)},
            )
        if upload_resp.status_code == 200:
            print(f"    Uploaded CV: {cv_path.name}")
        else:
            print(f"    FAILED to upload CV for {entry['full_name']}: "
                  f"{upload_resp.status_code} {upload_resp.text}")


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
        print(f"ERROR: '{CV_FOLDER}/' folder not found.")
        sys.exit(1)

    seed_jobs()
    seed_candidates()
    print("\nDone. Check the frontend or /docs to see the seeded data.")