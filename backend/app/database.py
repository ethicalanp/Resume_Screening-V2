from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./resume_screener.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CandidateCheck(Base):
    __tablename__ = "candidate_checks"

    id = Column(String, primary_key=True)
    jd_text = Column(Text)
    resume_text = Column(Text)
    resume_filename = Column(String)
    ats_score = Column(Float)
    semantic_score = Column(Float)
    keyword_score = Column(Float)
    matched_keywords = Column(JSON)
    missing_keywords = Column(JSON)
    ai_feedback = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    title = Column(String)
    company = Column(String)
    jd_text = Column(Text)
    jd_embedding = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Screening(Base):
    __tablename__ = "screenings"

    id = Column(String, primary_key=True)
    job_id = Column(String)
    resume_filename = Column(String)
    resume_text = Column(Text)
    ats_score = Column(Float)
    semantic_score = Column(Float)
    keyword_score = Column(Float)
    matched_keywords = Column(JSON)
    missing_keywords = Column(JSON)
    ai_summary = Column(Text)
    ai_feedback = Column(JSON)
    decision = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
