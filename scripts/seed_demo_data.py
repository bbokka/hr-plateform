"""Seed the running API with demo jobs + candidates for frontend testing.

Usage:
    1. Make sure your FastAPI server is running:
       uvicorn main:app --reload

    2. Make sure you have an existing user account in the database.

    3. Set the seed credentials:

       Windows PowerShell:
           $env:SEED_EMAIL="your-email@example.com"
           $env:SEED_PASSWORD="your-password"

       Linux/macOS:
           export SEED_EMAIL="your-email@example.com"
           export SEED_PASSWORD="your-password"

    4. Place CV files in sample_cvs/

    5. Run:
           python scripts/seed_demo_data.py

This script logs in through the real API first. The API sets the
httpOnly access_token cookie, and requests.Session() automatically
sends that cookie with all subsequent requests.
"""

import os
import sys
from pathlib import Path

import requests


API_BASE = "http://localhost:8000"

# Credentials of an existing user in your database.
SEED_EMAIL = os.getenv("SEED_EMAIL")
SEED_PASSWORD = os.getenv("SEED_PASSWORD")

COOKIE_NAME = "access_token"


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


# Explicit filename -> candidate mapping.
CV_FOLDER = Path("sample_cvs")

CANDIDATE_CV_MAP = [
    {
        "full_name": "Alex Morgan",
        "email": "alex.morgan@example.com",
        "cv_file": "Alex_Morgan_Software_Engineer_CV.pdf",
    },
    {
        "full_name": "David Chen",
        "email": "david.chen.ai@example.com",
        "cv_file": "David_Chen_Data_Scientist_CV.pdf",
    },
    {
        "full_name": "Elena Rostova",
        "email": "elena.rostova.design@example.com",
        "cv_file": "Elena_Rostova_UX_UI_Designer_CV.pdf",
    },
    {
        "full_name": "Byungjin Park",
        "email": "byungjin.park@example.com",
        "cv_file": "resume.pdf",
    },
    {
        "full_name": "Sarah Jenkins",
        "email": "sarah.jenkins@example.com",
        "cv_file": "Sarah_Jenkins_Marketing_Director_CV.pdf",
    },
    {
        "full_name": "aziz BenAmor",
        "email": "AzizBenAmor@example.com",
        "cv_file": "test_CV.pdf",
    },
]


def check_server(session: requests.Session) -> bool:
    """Check whether the API is reachable."""
    try:
        resp = session.get(f"{API_BASE}/health", timeout=3)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def login(session: requests.Session):
    """Login and store the JWT cookie in the requests session."""

    if not SEED_EMAIL or not SEED_PASSWORD:
        print("ERROR: Seed credentials are missing.")
        print()
        print("Set these environment variables before running the script:")
        print()
        print("Windows PowerShell:")
        print('  $env:SEED_EMAIL="your-email@example.com"')
        print('  $env:SEED_PASSWORD="your-password"')
        print()
        print("Linux/macOS:")
        print('  export SEED_EMAIL="your-email@example.com"')
        print('  export SEED_PASSWORD="your-password"')
        sys.exit(1)

    print(f"Logging in as {SEED_EMAIL}...")

    # OAuth2PasswordRequestForm expects form data:
    # username=<email>&password=<password>
    resp = session.post(
        f"{API_BASE}/auth/login",
        data={
            "username": SEED_EMAIL,
            "password": SEED_PASSWORD,
        },
        timeout=10,
    )

    if resp.status_code != 200:
        print(
            f"ERROR: Login failed: "
            f"{resp.status_code} {resp.text}"
        )
        sys.exit(1)

    # The JWT is returned as an httpOnly cookie.
    token = session.cookies.get(COOKIE_NAME)

    if not token:
        print(
            "ERROR: Login succeeded, but the access_token cookie "
            "was not received."
        )
        print(f"Cookies received: {session.cookies.get_dict()}")
        sys.exit(1)

    print("Login successful.")
    print("JWT access_token cookie received.\n")


def seed_jobs(session: requests.Session):
    print("Seeding jobs...")

    for job in DEMO_JOBS:
        resp = session.post(
            f"{API_BASE}/jobs",
            json=job,
            timeout=10,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            print(
                f"  Created job: {job['title']} "
                f"(id={data.get('id', 'unknown')})"
            )
        else:
            print(
                f"  FAILED to create job '{job['title']}': "
                f"{resp.status_code} {resp.text}"
            )


def seed_candidates(session: requests.Session):
    print("\nSeeding candidates...")

    for entry in CANDIDATE_CV_MAP:

        # Create candidate
        resp = session.post(
            f"{API_BASE}/candidates",
            json={
                "full_name": entry["full_name"],
                "email": entry["email"],
            },
            timeout=10,
        )

        if resp.status_code not in (200, 201):
            print(
                f"  FAILED to create candidate "
                f"'{entry['full_name']}': "
                f"{resp.status_code} {resp.text}"
            )
            continue

        candidate_id = resp.json()["id"]

        print(
            f"  Created candidate: {entry['full_name']} "
            f"(id={candidate_id})"
        )

        # Find CV
        cv_path = CV_FOLDER / entry["cv_file"]

        if not cv_path.exists():
            print(
                f"    WARNING: expected CV file not found: "
                f"{cv_path} — skipped"
            )
            continue

        # Upload CV
        with open(cv_path, "rb") as f:
            upload_resp = session.post(
                f"{API_BASE}/candidates/{candidate_id}/cv",
                files={
                    "file": (
                        cv_path.name,
                        f,
                        "application/pdf",
                    )
                },
                timeout=60,
            )

        if upload_resp.status_code in (200, 201):
            print(f"    Uploaded CV: {cv_path.name}")
        else:
            print(
                f"    FAILED to upload CV for "
                f"'{entry['full_name']}': "
                f"{upload_resp.status_code} "
                f"{upload_resp.text}"
            )


if __name__ == "__main__":

    # Create one persistent HTTP session.
    # This is important because the JWT is stored in a cookie.
    session = requests.Session()

    # Check API
    if not check_server(session):
        print(
            f"ERROR: could not reach {API_BASE}. "
            "Is `uvicorn main:app --reload` running?"
        )
        sys.exit(1)

    # Check CV folder
    if not CV_FOLDER.exists():
        print(
            f"ERROR: '{CV_FOLDER}/' folder not found."
        )
        sys.exit(1)

    # Authenticate first.
    login(session)

    # Now all protected requests automatically contain
    # the access_token cookie.
    seed_jobs(session)
    seed_candidates(session)

    print("\nDone. Check the frontend or /docs to see the seeded data.")