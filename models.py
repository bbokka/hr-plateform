from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from database import Base
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship



class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    embedding = Column(Vector(384), nullable=True)

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cv_file_path = Column(String, nullable=True)
    cv_raw_text = Column(Text, nullable=True)
    cv_parsed_data = Column(JSON, nullable=True)
    embedding = Column(Vector(384), nullable=True)  
    processing_status = Column(String, default="pending", nullable=False)
    processing_error = Column(String, nullable=True)



class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default="applied", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate = relationship("Candidate")
    job = relationship("Job")
    history = relationship("ApplicationStatusHistory", back_populates="application", order_by="ApplicationStatusHistory.changed_at")


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    status = Column(String, nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="history")