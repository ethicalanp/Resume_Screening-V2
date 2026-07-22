"""
ATS Scoring Engine.

Weighted multi-component score:
  40% Semantic similarity (Gemini embeddings + cosine)
  30% Keyword match rate (skill taxonomy)
  15% Experience relevance (heuristic)
  10% Education match (heuristic)
   5% Format quality (structure check)
"""

import re
from typing import List, Set, Tuple
import numpy as np

from app.services import gemini_service, keyword_extractor, parser


# ── Experience extraction ─────────────────────────────────────────────────────

YOE_PATTERNS = [
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
    r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
    r"(?:experience|exp)[:\s]+(\d+)\+?\s*(?:years?|yrs?)",
]

JD_YOE_PATTERNS = [
    r"(\d+)\+\s*(?:years?|yrs?)",
    r"(\d+)\s*(?:to|-)\s*(\d+)\s*(?:years?|yrs?)",
    r"minimum\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?)",
    r"at\s+least\s+(\d+)\s*(?:years?|yrs?)",
]


def _extract_yoe(text: str) -> int:
    """Try to extract years of experience from text."""
    text_lower = text.lower()
    for pattern in YOE_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            groups = [g for g in m.groups() if g is not None]
            return int(groups[0]) if groups else 0
    return 0


def _extract_required_yoe(jd_text: str) -> int:
    """Extract required years of experience from JD."""
    jd_lower = jd_text.lower()
    for pattern in JD_YOE_PATTERNS:
        m = re.search(pattern, jd_lower)
        if m:
            groups = [g for g in m.groups() if g is not None]
            return int(groups[0]) if groups else 0
    return 0


def _score_experience(resume_text: str, jd_text: str) -> float:
    """Score 0-1 based on experience years match."""
    resume_yoe = _extract_yoe(resume_text)
    required_yoe = _extract_required_yoe(jd_text)

    if required_yoe == 0:
        # No requirement stated → neutral score
        return 0.7

    if resume_yoe == 0:
        # Can't determine resume experience → slightly below neutral
        return 0.5

    if resume_yoe >= required_yoe:
        return 1.0
    else:
        # Partial credit proportional to how close they are
        ratio = resume_yoe / required_yoe
        return max(0.1, ratio)


# ── Education extraction ──────────────────────────────────────────────────────

DEGREE_LEVELS = {
    "phd": 5, "doctorate": 5, "doctoral": 5,
    "master": 4, "msc": 4, "mba": 4, "m.s": 4, "m.e": 4,
    "bachelor": 3, "bsc": 3, "b.e": 3, "b.tech": 3, "b.s": 3, "undergraduate": 3,
    "associate": 2, "diploma": 2,
    "high school": 1, "secondary": 1,
}


def _extract_degree_level(text: str) -> int:
    text_lower = text.lower()
    for degree, level in sorted(DEGREE_LEVELS.items(), key=lambda x: -x[1]):
        if degree in text_lower:
            return level
    return 0


def _score_education(resume_text: str, jd_text: str) -> float:
    """Score 0-1 based on education level match."""
    jd_level = _extract_degree_level(jd_text)
    resume_level = _extract_degree_level(resume_text)

    if jd_level == 0:
        return 0.8  # No requirement stated
    if resume_level == 0:
        return 0.5  # Can't determine

    if resume_level >= jd_level:
        return 1.0
    else:
        diff = jd_level - resume_level
        return max(0.1, 1.0 - diff * 0.25)


# ── Format quality ────────────────────────────────────────────────────────────

def _score_format(resume_text: str) -> float:
    """Score 0-1 based on resume structural quality."""
    stats = parser.get_resume_stats(resume_text)
    score = 0.0

    # Word count (ideal: 300–800 words)
    wc = stats["word_count"]
    if 300 <= wc <= 800:
        score += 0.3
    elif 200 <= wc <= 1200:
        score += 0.2
    else:
        score += 0.1

    # Has contact info
    if stats["has_contact_info"]:
        score += 0.2

    # Has bullet points
    if stats["bullet_count"] >= 3:
        score += 0.2

    # Has at least 2 sections
    if stats["section_count"] >= 2:
        score += 0.2

    # Has key sections
    important = {"skills", "experience", "education"}
    if important & set(stats["sections_found"]):
        score += 0.1

    return min(score, 1.0)


# ── Cosine similarity ─────────────────────────────────────────────────────────

def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ── Main scoring function ─────────────────────────────────────────────────────

async def score_resume_against_jd(
    resume_text: str,
    jd_text: str,
    jd_embedding: List[float] = None,
) -> dict:
    """
    Full ATS scoring pipeline.

    Args:
        resume_text: Parsed resume text
        jd_text: Job description text
        jd_embedding: Pre-computed JD embedding (optional, avoids re-embedding)

    Returns:
        Dict with ats_score, component scores, matched/missing keywords
    """
    # 1. Embeddings (async, in parallel)
    import asyncio
    if jd_embedding:
        resume_emb_task = gemini_service.get_embedding(resume_text)
        resume_emb = await resume_emb_task
        jd_emb = jd_embedding
    else:
        resume_emb, jd_emb = await asyncio.gather(
            gemini_service.get_embedding(resume_text),
            gemini_service.get_embedding(jd_text),
        )

    # 2. Semantic similarity
    semantic_score = _cosine_similarity(resume_emb, jd_emb)
    # Normalize: cosine can return 0-1 for positive embeddings
    # Clamp to [0, 1]
    semantic_score = max(0.0, min(1.0, semantic_score))

    # 3. Keyword extraction & matching
    # Use the job description to drive the keyword set, including non-technical business and role keywords.
    jd_keywords: Set[str] = keyword_extractor.extract_keywords(jd_text)
    resume_keywords: Set[str] = keyword_extractor.extract_keywords(resume_text)

    matched: Set[str] = jd_keywords & resume_keywords
    missing: Set[str] = jd_keywords - resume_keywords

    keyword_score = len(matched) / max(len(jd_keywords), 1)

    # 4. Experience match
    exp_score = _score_experience(resume_text, jd_text)

    # 5. Education match
    edu_score = _score_education(resume_text, jd_text)

    # 6. Format quality
    format_score = _score_format(resume_text)

    # 7. Weighted composite ATS score
    ats_score = (
        0.40 * semantic_score
        + 0.30 * keyword_score
        + 0.15 * exp_score
        + 0.10 * edu_score
        + 0.05 * format_score
    ) * 100

    return {
        "ats_score": round(min(ats_score, 100.0), 1),
        "semantic_score": round(semantic_score * 100, 1),
        "keyword_score": round(keyword_score * 100, 1),
        "exp_score": round(exp_score * 100, 1),
        "edu_score": round(edu_score * 100, 1),
        "format_score": round(format_score * 100, 1),
        "matched_keywords": sorted(list(matched)),
        "missing_keywords": sorted(list(missing)),
        "jd_keywords_total": len(jd_keywords),
        # Return embedding for caching on HR side
        "_resume_embedding": resume_emb,
        "_jd_embedding": jd_emb if not jd_embedding else None,
    }
