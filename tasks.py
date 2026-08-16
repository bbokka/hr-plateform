from celery_app import celery_app
from database import SessionLocal
from models import Candidate
from services.cv_extraction import extract_text_from_cv
from services.cv_parser import parse_cv
from services.embedding_service import embed_text, build_candidate_embedding_text


@celery_app.task(bind=True, name="tasks.process_cv")
def process_cv(self, candidate_id: int, file_path: str):
    """Background job: extract text, run NLP parsing, generate the embedding,
    and persist everything onto the Candidate row.
    """
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return {"status": "failed", "error": "candidate_not_found"}

        candidate.processing_status = "processing"
        db.commit()

        raw_text = extract_text_from_cv(file_path)
        parsed_data = parse_cv(raw_text)

        embedding_text = build_candidate_embedding_text(raw_text, parsed_data)
        embedding = embed_text(embedding_text)

        candidate.cv_raw_text = raw_text
        candidate.cv_parsed_data = parsed_data
        candidate.embedding = embedding
        candidate.processing_status = "completed"
        candidate.processing_error = None
        db.commit()

        return {"status": "completed", "candidate_id": candidate_id}

    except Exception as exc:
        db.rollback()
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.processing_status = "failed"
            candidate.processing_error = str(exc)
            db.commit()
        raise

    finally:
        db.close()