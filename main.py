from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Job, Candidate
import shutil
import uuid
from pathlib import Path
from services.cv_extraction import extract_text_from_cv
from services.cv_parser import parse_cv
from services.embedding_service import embed_text, build_candidate_embedding_text
from tasks import process_cv

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

class JobCreate(BaseModel):
    title: str
    description: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    new_job = Job(title=job.title, description=job.description)
    new_job.embedding = embed_text(job.description)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).all()

@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


class CandidateCreate(BaseModel):
    full_name: str
    email: str

@app.post("/candidates")
def create_candidate(candidate: CandidateCreate, db: Session = Depends(get_db)):
    new_candidate = Candidate(full_name=candidate.full_name, email=candidate.email)
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)
    return new_candidate

@app.get("/candidates")
def list_candidates(db: Session = Depends(get_db)):
    return db.query(Candidate).all()

@app.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@app.post("/candidates/{candidate_id}/cv")
def upload_cv(candidate_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
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

@app.get("/jobs/{job_id}/matches")
def get_job_matches(job_id: int, limit: int = 5, db: Session = Depends(get_db)):
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

    return [
        {
            "candidate_id": c.Candidate.id,
            "full_name": c.Candidate.full_name,
            "email": c.Candidate.email,
            "similarity_score": round(1 - c.distance, 4),  # convert distance to similarity: 1 = perfect match
            "skills": (c.Candidate.cv_parsed_data or {}).get("skills", []),
        }
        for c in candidates
    ]
