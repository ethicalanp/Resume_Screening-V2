"""
Gemini API service: embeddings + AI explanations/feedback.
Uses gemini-1.5-flash for text generation and text-embedding-004 for embeddings.
"""

import os
import json
import asyncio
import re
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = genai.GenerativeModel("gemini-1.5-flash")
    return _model


async def get_embedding(text: str) -> List[float]:
    """Get text embedding using Gemini text-embedding-004."""
    if not GEMINI_API_KEY:
        # Return a zero vector as fallback (for testing without API key)
        return [0.0] * 768

    # Trim to avoid token limits (embedding model has limits)
    text_trimmed = text[:8000] if len(text) > 8000 else text

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: genai.embed_content(
                model="models/text-embedding-004",
                content=text_trimmed,
                task_type="retrieval_document",
            ),
        )
        return result["embedding"]
    except Exception as e:
        print(f"Embedding error: {e}")
        return [0.0] * 768


async def get_candidate_feedback(
    resume_text: str,
    jd_text: str,
    matched_keywords: List[str],
    missing_keywords: List[str],
    semantic_score: float,
    keyword_score: float,
) -> dict:
    """
    Generate detailed candidate-facing feedback.
    Returns structured JSON with strengths, improvements, section feedback, verdict.
    """
    if not GEMINI_API_KEY:
        return _mock_candidate_feedback(matched_keywords, missing_keywords, semantic_score)

    # Trim inputs to avoid token limits
    resume_trimmed = resume_text[:4000]
    jd_trimmed = jd_text[:2000]

    prompt = f"""You are an expert resume coach and ATS specialist. Analyze this resume against the job description and provide structured, actionable feedback.

JOB DESCRIPTION:
{jd_trimmed}

RESUME:
{resume_trimmed}

ATS ANALYSIS RESULTS:
- Semantic match: {semantic_score:.0%}
- Keyword match rate: {keyword_score:.0%}
- Keywords found: {', '.join(matched_keywords[:20]) if matched_keywords else 'None'}
- Keywords missing: {', '.join(missing_keywords[:20]) if missing_keywords else 'None'}

Respond ONLY with a valid JSON object (no markdown, no backticks) with this exact structure:
{{
  "overall_summary": "2-3 sentence overall assessment of fit for this role",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvements": [
    {{
      "issue": "specific gap or weakness",
      "suggestion": "concrete actionable advice",
      "example": "example phrase or rewrite if applicable (or empty string)"
    }}
  ],
  "section_feedback": {{
    "skills": "specific feedback on the skills section",
    "experience": "specific feedback on experience section",
    "education": "feedback on education section"
  }},
  "verdict": "STRONG_MATCH"
}}

For verdict, use exactly one of: STRONG_MATCH, GOOD_MATCH, PARTIAL_MATCH, WEAK_MATCH
- STRONG_MATCH: semantic > 75% and keyword > 70%
- GOOD_MATCH: semantic > 60% and keyword > 50%
- PARTIAL_MATCH: semantic > 40% or keyword > 30%
- WEAK_MATCH: otherwise

Provide 3-5 improvements. Be specific, honest, and constructive. Focus on what will actually improve ATS pass rate."""

    try:
        model = _get_model()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(prompt),
        )
        raw = response.text.strip()
        # Strip markdown code blocks if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError:
        return _mock_candidate_feedback(matched_keywords, missing_keywords, semantic_score)
    except Exception as e:
        print(f"Gemini feedback error: {e}")
        return _mock_candidate_feedback(matched_keywords, missing_keywords, semantic_score)


async def get_hr_summary(
    resume_text: str,
    jd_text: str,
    matched_keywords: List[str],
    missing_keywords: List[str],
    ats_score: float,
) -> str:
    """Generate a concise 3-sentence HR-facing candidate summary."""
    if not GEMINI_API_KEY:
        return f"Candidate scored {ats_score:.0f}% on ATS matching. Matched keywords: {', '.join(matched_keywords[:5])}. Review recommended."

    resume_trimmed = resume_text[:3000]
    jd_trimmed = jd_text[:1500]

    prompt = f"""You are an expert recruiter assistant. Write a concise 3-sentence summary of this candidate for a hiring manager.

JOB DESCRIPTION (brief):
{jd_trimmed}

CANDIDATE RESUME (brief):
{resume_trimmed}

ATS SCORE: {ats_score:.0f}%
MATCHED SKILLS: {', '.join(matched_keywords[:15])}
MISSING SKILLS: {', '.join(missing_keywords[:10])}

Write exactly 3 sentences:
1. Who the candidate is and their strongest qualification
2. Key matched skills and relevant experience for this role
3. Notable gaps or considerations for the hiring manager

Be factual and professional. Output plain text only (no JSON, no markdown)."""

    try:
        model = _get_model()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(prompt),
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini summary error: {e}")
        return f"Candidate scored {ats_score:.0f}% on ATS matching. Matched keywords: {', '.join(matched_keywords[:5])}. Review recommended."


def _mock_candidate_feedback(
    matched_keywords: List[str],
    missing_keywords: List[str],
    semantic_score: float,
) -> dict:
    """Fallback feedback when API key is not set."""
    if semantic_score > 0.75:
        verdict = "STRONG_MATCH"
        summary = "Your resume shows strong alignment with the job requirements."
    elif semantic_score > 0.55:
        verdict = "GOOD_MATCH"
        summary = "Your resume shows good alignment with several key requirements."
    elif semantic_score > 0.35:
        verdict = "PARTIAL_MATCH"
        summary = "Your resume partially matches the job description. Several gaps exist."
    else:
        verdict = "WEAK_MATCH"
        summary = "Your resume needs significant improvement for this role."

    return {
        "overall_summary": summary + f" You matched {len(matched_keywords)} key skills.",
        "strengths": [f"Strong match on: {kw}" for kw in matched_keywords[:3]] or ["Relevant background detected"],
        "improvements": [
            {
                "issue": f"Missing keyword: {kw}",
                "suggestion": f"Add '{kw}' to your skills or experience section where relevant.",
                "example": "",
            }
            for kw in missing_keywords[:4]
        ] or [{"issue": "Add more specific technical skills", "suggestion": "Expand your skills section", "example": ""}],
        "section_feedback": {
            "skills": "Ensure your skills section lists all relevant technologies explicitly.",
            "experience": "Quantify achievements with metrics where possible (e.g. 'reduced load time by 40%').",
            "education": "Education section looks standard. Add relevant certifications if any.",
        },
        "verdict": verdict,
    }
