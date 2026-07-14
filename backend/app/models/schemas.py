from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# ── Candidate Portal ─────────────────────────────────────────────────────────

class AIFeedback(BaseModel):
    overall_summary: str
    strengths: List[str]
    improvements: List[Dict[str, str]]
    section_feedback: Dict[str, str]
    verdict: str  # STRONG_MATCH | GOOD_MATCH | PARTIAL_MATCH | WEAK_MATCH


class CandidateCheckResult(BaseModel):
    id: str
    resume_filename: str
    ats_score: float
    semantic_score: float
    keyword_score: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    ai_feedback: AIFeedback
    created_at: datetime

    class Config:
        from_attributes = True


# ── HR Portal ─────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    company: str
    jd_text: str


class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    jd_text: str
    created_at: datetime
    screening_count: int = 0

    class Config:
        from_attributes = True


class ScreeningResponse(BaseModel):
    id: str
    job_id: str
    resume_filename: str
    ats_score: float
    semantic_score: float
    keyword_score: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    ai_summary: str
    ai_feedback: Optional[Dict[str, Any]]
    decision: str
    created_at: datetime

    class Config:
        from_attributes = True


class DecisionUpdate(BaseModel):
    decision: str  # shortlist | reject | hold | pending
