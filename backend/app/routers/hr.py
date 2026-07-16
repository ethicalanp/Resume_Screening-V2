"""
HR Portal API routes.
Manages job postings, bulk resume screening, and hiring decisions.
"""

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db, Job, Screening
from app.models.schemas import JobCreate, JobResponse, ScreeningResponse, DecisionUpdate
from app.services import parser, scorer, gemini_service

router = APIRouter(prefix="/api/hr", tags=["HR Portal"])


# ── Job Postings ──────────────────────────────────────────────────────────────

@router.post("/jobs", response_model=JobResponse)
async def create_job(job: JobCreate, db: Session = Depends(get_db)):
    """Create a new job posting with JD. Embeds the JD immediately for faster screening."""
    if len(job.jd_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Job description too short.")

    # Embed JD now so screening is faster later
    jd_embedding = await gemini_service.get_embedding(job.jd_text)

    job_id = str(uuid.uuid4())
    db_job = Job(
        id=job_id,
        title=job.title,
        company=job.company,
        jd_text=job.jd_text,
        jd_embedding=jd_embedding,
        created_at=datetime.utcnow(),
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    return JobResponse(
        id=db_job.id,
        title=db_job.title,
        company=db_job.company,
        jd_text=db_job.jd_text,
        created_at=db_job.created_at,
        screening_count=0,
    )


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """List all job postings with screening count."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    result = []
    for job in jobs:
        count = db.query(Screening).filter(Screening.job_id == job.id).count()
        result.append(
            JobResponse(
                id=job.id,
                title=job.title,
                company=job.company,
                jd_text=job.jd_text,
                created_at=job.created_at,
                screening_count=count,
            )
        )
    return result


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a specific job posting."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    count = db.query(Screening).filter(Screening.job_id == job_id).count()
    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        jd_text=job.jd_text,
        created_at=job.created_at,
        screening_count=count,
    )


# ── Resume Screening ──────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/screen", response_model=ScreeningResponse)
async def screen_resume(
    job_id: str,
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a resume for a job posting and get ATS score + AI summary."""
    # ── Fetch job ─────────────────────────────────────────────────────────────
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # ── Validate file ─────────────────────────────────────────────────────────
    filename = resume.filename or "resume"
    if not filename.lower().endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file. Upload a PDF or DOCX.",
        )

    file_bytes = await resume.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB).")

    # ── Parse ─────────────────────────────────────────────────────────────────
    try:
        resume_text = parser.parse_resume(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if len(resume_text.strip()) < 100:
        raise HTTPException(status_code=422, detail="Could not extract enough text from the resume.")

    # ── Score (use cached JD embedding) ──────────────────────────────────────
    score_result = await scorer.score_resume_against_jd(
        resume_text=resume_text,
        jd_text=job.jd_text,
        jd_embedding=job.jd_embedding,
    )

    # ── AI Summary (HR-facing, concise) ──────────────────────────────────────
    ai_summary = await gemini_service.get_hr_summary(
        resume_text=resume_text,
        jd_text=job.jd_text,
        matched_keywords=score_result["matched_keywords"],
        missing_keywords=score_result["missing_keywords"],
        ats_score=score_result["ats_score"],
    )

    # ── AI Detailed Feedback ──────────────────────────────────────────────────
    ai_feedback = await gemini_service.get_candidate_feedback(
        resume_text=resume_text,
        jd_text=job.jd_text,
        matched_keywords=score_result["matched_keywords"],
        missing_keywords=score_result["missing_keywords"],
        semantic_score=score_result["semantic_score"] / 100,
        keyword_score=score_result["keyword_score"] / 100,
    )

    # ── Persist ───────────────────────────────────────────────────────────────
    screening_id = str(uuid.uuid4())
    db_screening = Screening(
        id=screening_id,
        job_id=job_id,
        resume_filename=filename,
        resume_text=resume_text,
        ats_score=score_result["ats_score"],
        semantic_score=score_result["semantic_score"],
        keyword_score=score_result["keyword_score"],
        matched_keywords=score_result["matched_keywords"],
        missing_keywords=score_result["missing_keywords"],
        ai_summary=ai_summary,
        ai_feedback=ai_feedback,
        decision="pending",
        created_at=datetime.utcnow(),
    )
    db.add(db_screening)
    db.commit()
    db.refresh(db_screening)

    return _to_response(db_screening)


@router.get("/jobs/{job_id}/screenings", response_model=List[ScreeningResponse])
def list_screenings(job_id: str, db: Session = Depends(get_db)):
    """Get all screenings for a job, sorted by ATS score descending."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    screenings = (
        db.query(Screening)
        .filter(Screening.job_id == job_id)
        .order_by(Screening.ats_score.desc())
        .all()
    )
    return [_to_response(s) for s in screenings]


@router.get("/jobs/{job_id}/screenings/{screening_id}", response_model=ScreeningResponse)
def get_screening(job_id: str, screening_id: str, db: Session = Depends(get_db)):
    """Get a specific screening result."""
    s = (
        db.query(Screening)
        .filter(Screening.id == screening_id, Screening.job_id == job_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Screening not found.")
    return _to_response(s)


@router.patch("/jobs/{job_id}/screenings/{screening_id}/decision")
def update_decision(
    job_id: str,
    screening_id: str,
    body: DecisionUpdate,
    db: Session = Depends(get_db),
):
    """Update the HR decision for a candidate (shortlist / reject / hold / pending)."""
    valid_decisions = {"pending", "shortlist", "reject", "hold"}
    if body.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision. Must be one of: {valid_decisions}",
        )

    s = (
        db.query(Screening)
        .filter(Screening.id == screening_id, Screening.job_id == job_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Screening not found.")

    s.decision = body.decision
    db.commit()
    return {"id": screening_id, "decision": body.decision}


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(s: Screening) -> ScreeningResponse:
    return ScreeningResponse(
        id=s.id,
        job_id=s.job_id,
        resume_filename=s.resume_filename,
        ats_score=s.ats_score,
        semantic_score=s.semantic_score,
        keyword_score=s.keyword_score,
        matched_keywords=s.matched_keywords or [],
        missing_keywords=s.missing_keywords or [],
        ai_summary=s.ai_summary or "",
        ai_feedback=s.ai_feedback,
        decision=s.decision,
        created_at=s.created_at,
    )
