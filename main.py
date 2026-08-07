from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Job, Candidate
import shutil
import uuid
from pathlib import Path
from services.cv_extraction import extract_text_from_cv


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app = FastAPI()

class JobCreate(BaseModel):
    title: str
    description: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    new_job = Job(title=job.title, description=job.description)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).all()


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

    raw_text = extract_text_from_cv(str(file_path))

    candidate.cv_file_path = str(file_path)
    candidate.cv_raw_text = raw_text
    db.commit()
    db.refresh(candidate)

    return {
        "candidate_id": candidate.id,
        "cv_file_path": candidate.cv_file_path,
        "cv_raw_text_preview": raw_text[:200]
    }