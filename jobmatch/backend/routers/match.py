"""
routers/match.py — On-Demand Resume Re-Scoring
===================================================
Your original Streamlit app scored a resume exactly once: the moment the
seeker submitted their application (inside show_application_form()'s
submit handler, now ported into POST /applications in routers/applications.py).
There was no "re-score" button anywhere in the UI.

This file adds that capability for the REST API, for two practical reasons:
  1. If predict_single() or the model file (resume_model.pkl) gets
     retrained/updated, existing applications keep their stale score
     until something re-runs them through the new model.
  2. An employer reviewing a borderline "Review Needed" applicant may
     want to re-check the score after, say, asking the candidate to
     re-upload a clearer resume.

ENDPOINTS:
  POST /match/rescore/{application_id}   → re-run ML scoring for one
                                             existing application (employer,
                                             job owner only)
  POST /match/rescore-job/{job_id}       → re-run scoring for every
                                             applicant on one job at once
                                             (employer, job owner only)

NOTE ON ARCHITECTURE:
  All actual scoring logic (score_resume, the loaded model bundle,
  _detect_job_category, etc.) lives in routers/applications.py — that's
  the single source of truth, matching how your original app only ever
  scored inside apply.py. This file imports from there rather than
  duplicating the formula, so the two never drift out of sync.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, status

import db
from auth_utils import require_employer
from models import MatchResult

# Reuse the exact scoring logic + loaded model from applications.py —
# single source of truth, same as the original app only scoring in apply.py.
from routers.applications import score_resume, MODEL_LOADED

router = APIRouter(prefix="/match", tags=["Matching"])


# HELPER — re-parse + re-score a single application
async def _rescore_application(application: dict, job: dict) -> dict:
    """Re-reads the application's stored resume PDF from disk, re-parses it,
    and re-runs score_resume() against the given job.

    Returns a dict: { application_id, ai_score, ml_label, matched_skills, missing_skills }
    or a dict with ai_score=None if there's no resume on file to re-score.
    """
    resume_path = application.get("resume_path")

    if not resume_path or not Path(resume_path).exists():
        return {
            "application_id": application["id"],
            "ai_score": None,
            "ml_label": "No resume on file",
            "matched_skills": [],
            "missing_skills": [],
        }

    from ..resume_parser import parse_resume

    with open(resume_path, "rb") as f:
        parsed_resume = parse_resume(f)

    if not parsed_resume.get("raw_text"):
        return {
            "application_id": application["id"],
            "ai_score": None,
            "ml_label": "Could not extract resume text",
            "matched_skills": [],
            "missing_skills": [],
        }
    score, label, matched_skills, missing_skills = score_resume(parsed_resume, job=job)

    await db.update_application_score(application["id"], score, label)

    return {
        "application_id": application["id"],
        "ai_score": score,
        "ml_label": label,
        "matched_skills": matched_skills[:6],
        "missing_skills": missing_skills[:6],
    }


# RE-SCORE ONE APPLICATION
@router.post(
    "/rescore/{application_id}",
    response_model=MatchResult,
    summary="Re-run ML scoring for a single application (employer, job owner only)",
)
async def rescore_application(
        application_id: int,
        current_user: dict = Depends(require_employer),
):
    """
        Re-parses the stored resume PDF and re-scores it against the job,
        overwriting the application's ai_score/ml_label.
        Only the employer who owns the underlying job can trigger this.
        """
    application = await db.get_application_by_id(application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")

    job = await db.get_job_by_id(application["job_id"])
    if job is None or job["employer_id"] != current_user["id"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only re-score applicants for your own Jobs.",
        )
    result = await _rescore_application(application, job)

    if result["ai_score"] is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, result["ml_label"])

    return MatchResult(
        application_id=result["application_id"],
        job_id=job["id"],
        ai_score=result["ai_score"],
        ml_label=result["ml_label"],
        details=(
            f"Matched: {', '.join(result['matched_skills']) or 'none'}. "
            f"Missing: {', '.join(result['missing_skills']) or 'none'}."
        ),
    )
# RE-SCORE EVERY APPLICANT FOR A JOB
@router.post(
    "/rescore-job/{job_id}",
    summary="Re-run ML scoring for every applicant on a job (employer, job owner only)",
)
async def rescore_all_applicants(
        job_id: int,
        current_user: dict = Depends(require_employer),
):
    """
        Bulk version of /rescore/{application_id} — useful right after
        retraining train_model.py's model and reloading resume_model.pkl,
        so every existing applicant's score reflects the new model.
        """
    job = await db.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")

    if job["employer_id"] != current_user["id"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only re-score applicants for your own jobs.",
        )

    applications = await db.get_applications_by_job(job_id)

    results = []
    for application in applications:
        result = await _rescore_application(application, job)
        results.append(result)

    return {
        "job_id": job_id,
        "rescored_count": len(results),
        "model_loaded": MODEL_LOADED,
        "results": results,
    }

