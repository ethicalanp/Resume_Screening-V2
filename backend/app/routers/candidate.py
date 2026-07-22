"""
Candidate Portal API routes.
No authentication required — session-based anonymous checks.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db, CandidateCheck
from app.models.schemas import CandidateCheckResult
from app.services import parser, scorer, AI_service

router = APIRouter(prefix="/api/candidate", tags=["Candidate"])


@router.post("/check", response_model=CandidateCheckResult)
async def check_resume(
    resume: UploadFile = File(...),
    jd_text: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Upload a resume + job description → get ATS score + improvement feedback.
    No login required.
    """
    # ── Validate file ─────────────────────────────────────────────────────────
    if not resume.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    filename = resume.filename
    if not filename.lower().endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a PDF or DOCX file.",
        )

    if not jd_text or len(jd_text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Please provide a complete job description (at least 50 characters).",
        )

    # ── Parse resume ──────────────────────────────────────────────────────────
    file_bytes = await resume.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    try:
        resume_text = parser.parse_resume(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if len(resume_text.strip()) < 100:
        raise HTTPException(
            status_code=422,
            detail="Could not extract enough text from the resume. Try a different file.",
        )

    # ── Score ──────────────────────────────────────────────────────────────────
    score_result = await scorer.score_resume_against_jd(resume_text, jd_text)

    # ── AI Feedback ───────────────────────────────────────────────────────────
    ai_feedback = await AI_service.get_candidate_feedback(
        resume_text=resume_text,
        jd_text=jd_text,
        matched_keywords=score_result["matched_keywords"],
        missing_keywords=score_result["missing_keywords"],
        semantic_score=score_result["semantic_score"] / 100,
        keyword_score=score_result["keyword_score"] / 100,
    )

    # ── Persist ───────────────────────────────────────────────────────────────
    check_id = str(uuid.uuid4())
    db_record = CandidateCheck(
        id=check_id,
        jd_text=jd_text,
        resume_text=resume_text,
        resume_filename=filename,
        ats_score=score_result["ats_score"],
        semantic_score=score_result["semantic_score"],
        keyword_score=score_result["keyword_score"],
        matched_keywords=score_result["matched_keywords"],
        missing_keywords=score_result["missing_keywords"],
        ai_feedback=ai_feedback,
        created_at=datetime.utcnow(),
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return CandidateCheckResult(
        id=check_id,
        resume_filename=filename,
        ats_score=score_result["ats_score"],
        semantic_score=score_result["semantic_score"],
        keyword_score=score_result["keyword_score"],
        matched_keywords=score_result["matched_keywords"],
        missing_keywords=score_result["missing_keywords"],
        ai_feedback=ai_feedback,
        created_at=db_record.created_at,
    )


@router.get("/check/{check_id}", response_model=CandidateCheckResult)
async def get_check_result(check_id: str, db: Session = Depends(get_db)):
    """Retrieve a previously computed check result by ID."""
    record = db.query(CandidateCheck).filter(CandidateCheck.id == check_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Check result not found.")

    return CandidateCheckResult(
        id=record.id,
        resume_filename=record.resume_filename,
        ats_score=record.ats_score,
        semantic_score=record.semantic_score,
        keyword_score=record.keyword_score,
        matched_keywords=record.matched_keywords or [],
        missing_keywords=record.missing_keywords or [],
        ai_feedback=record.ai_feedback or {},
        created_at=record.created_at,
    )
