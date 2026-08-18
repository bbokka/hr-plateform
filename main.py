from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Job, Candidate, Application, ApplicationStatusHistory, User
import shutil
import uuid
from pathlib import Path
from services.embedding_service import embed_text
from tasks import process_cv
from fastapi import Response
from auth import hash_password, verify_password, create_access_token, get_current_user, COOKIE_NAME, COOKIE_SECURE


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------

class JobCreate(BaseModel):
    title: str
    description: str


class CandidateCreate(BaseModel):
    full_name: str
    email: str


class ApplicationCreate(BaseModel):
    candidate_id: int
    job_id: int


class ApplicationStatusUpdate(BaseModel):
    status: str


class UserRegister(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# Health (public)
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Authentication (public)
# ---------------------------------------------------------------------------

@app.post("/auth/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(email=user.email, hashed_password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email}


@app.post("/auth/login")
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(data={"sub": user.email})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=60 * 60 * 24,
        path="/",
    )
    return {"email": user.email}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Lets the frontend check 'am I logged in' on page load without
    needing to store anything client-side -- the browser sends the cookie
    automatically, and this either succeeds or 401s."""
    return {"id": current_user.id, "email": current_user.email}


# ---------------------------------------------------------------------------
# Jobs (protected)
# ---------------------------------------------------------------------------

@app.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_job = Job(title=job.title, description=job.description)
    new_job.embedding = embed_text(job.description)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Job).all()


@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs/{job_id}/matches")
def get_job_matches(
    job_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ranked candidates by semantic similarity, merged with each
    candidate's current application status (if any) for this job -- so the
    frontend can render a single view: 'Add to Pipeline' for candidates with
    no application yet, or their current stage badge if they do.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.embedding is None:
        raise HTTPException(status_code=400, detail="Job has no embedding yet")

    candidates = (
        db.query(
            Candidate,
            Candidate.embedding.cosine_distance(job.embedding).label("distance")
        )
        .filter(Candidate.embedding.isnot(None))
        .order_by("distance")
        .limit(limit)
        .all()
    )

    results = []
    for c in candidates:
        application = (
            db.query(Application)
            .filter(
                Application.candidate_id == c.Candidate.id,
                Application.job_id == job_id,
            )
            .first()
        )
        results.append({
            "candidate_id": c.Candidate.id,
            "full_name": c.Candidate.full_name,
            "email": c.Candidate.email,
            "similarity_score": round(1 - c.distance, 4),  # convert distance to similarity: 1 = perfect match
            "skills": (c.Candidate.cv_parsed_data or {}).get("skills", []),
            "application_id": application.id if application else None,
            "application_status": application.status if application else None,
        })

    return results


# ---------------------------------------------------------------------------
# Candidates (protected)
# ---------------------------------------------------------------------------

@app.post("/candidates")
def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_candidate = Candidate(full_name=candidate.full_name, email=candidate.email)
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)
    return new_candidate


@app.get("/candidates")
def list_candidates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Candidate).all()


@app.get("/candidates/{candidate_id}")
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@app.post("/candidates/{candidate_id}/cv")
def upload_cv(
    candidate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save the uploaded file and queue background processing (text
    extraction, NLP parsing, embedding generation -- see tasks.process_cv).
    Returns immediately; the candidate's processing_status can be polled
    via GET /candidates/{candidate_id}.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX are supported")

    stored_filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / stored_filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    candidate.cv_file_path = str(file_path)
    candidate.processing_status = "pending"
    candidate.processing_error = None
    db.commit()
    db.refresh(candidate)

    process_cv.delay(candidate.id, str(file_path))

    return {
        "candidate_id": candidate.id,
        "cv_file_path": candidate.cv_file_path,
        "processing_status": candidate.processing_status,
    }


# ---------------------------------------------------------------------------
# Applications / tracking pipeline (protected)
# ---------------------------------------------------------------------------

@app.post("/applications")
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == application.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = (
        db.query(Application)
        .filter(
            Application.candidate_id == application.candidate_id,
            Application.job_id == application.job_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Application already exists for this candidate and job")

    new_application = Application(
        candidate_id=application.candidate_id,
        job_id=application.job_id,
        status="applied",
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)

    db.add(ApplicationStatusHistory(application_id=new_application.id, status="applied"))
    db.commit()

    return new_application


@app.get("/applications/{application_id}")
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@app.patch("/applications/{application_id}/status")
def update_application_status(
    application_id: int,
    update: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = update.status
    db.commit()
    db.refresh(application)

    db.add(ApplicationStatusHistory(application_id=application.id, status=update.status))
    db.commit()

    return application


@app.get("/applications/{application_id}/history")
def get_application_history(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return (
        db.query(ApplicationStatusHistory)
        .filter(ApplicationStatusHistory.application_id == application_id)
        .order_by(ApplicationStatusHistory.changed_at)
        .all()
    )


@app.get("/jobs/{job_id}/applications")
def list_job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All tracked applications for a job -- the dashboard/pipeline view
    data source, independent of similarity ranking."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    applications = db.query(Application).filter(Application.job_id == job_id).all()

    return [
        {
            "application_id": a.id,
            "candidate_id": a.candidate.id,
            "full_name": a.candidate.full_name,
            "email": a.candidate.email,
            "status": a.status,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }
        for a in applications
    ]