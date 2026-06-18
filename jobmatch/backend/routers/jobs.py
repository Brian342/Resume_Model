"""
routers/jobs.py — Job Posting CRUD Endpoints
===============================================
This is the REST equivalent of employer_dashboard.py (posting/editing/
deleting jobs) and the job board portion of seeker_dashboard.py
(browsing active jobs).

ENDPOINTS:
  POST   /jobs                → employer creates a new job posting
  GET    /jobs                → seeker browses active jobs (with preference filtering)
  GET    /jobs/mine           → employer views their own postings (active + inactive)
  GET    /jobs/{job_id}       → anyone views a single job's detail page
  PATCH  /jobs/{job_id}       → employer edits a job
  PATCH  /jobs/{job_id}/toggle→ employer activates/deactivates a job
  DELETE /jobs/{job_id}       → employer permanently deletes a job + its applications

PERMISSION MODEL:
  - Browsing jobs (GET) is open to any logged-in user.
  - Creating, editing, toggling, deleting → employer only, AND only
    the employer who owns that specific job (checked per-route below).
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional

from .. import db
from ..auth_utils import get_current_user, require_employer
from ..models import JobCreated, JobUpdate, JobOut, MessageResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# HELPER — ownership check
# Used by every route that modifies a job, so an employer can't
# edit or delete another employer's posting.
async def _get_owned_job_or_404(job_id: int, employer_id: int) -> dict:
    """
    Fetches a job and verifies the given employer owns it.
    Raises 404 if the job doesn't exist, 403 if it belongs to someone else
    """
    job = await db.get_job_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    if job["employer_id"] != employer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify jobs you posted"
        )

    return job

# CREATE  — mirrors create_job() called from employer_dashboard.py
@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a new job listing (employer only)",
)

async def create_job(
        job_in:JobCreated,
        current_user: dict = Depends(require_employer),
):
    """
       Creates a new job posting owned by the logged-in employer.
       Field validation (non-empty title/company/etc.) already happened
       in the JobCreate Pydantic model.
       """
    job_id = await db.create_job(
        employer_id=current_user["id"],
        title=job_in.title,
        company=job_in.company,
        location=job_in.location,
        description=job_in.description,
        requirements=job_in.requirements,
        salary=job_in.salary or "",
    )

    return MessageResponse(message=f"Job Posted Successfully (id={job_id}).")

# LIST ACTIVE JOBS  — mirrors the job board in seeker_dashboard.py

@router.get(
    "",
    response_model=list[JobOut],
    summary="Browse all active job listings",
)
async def list_active_jobs(
        use_preferences: bool = True,
        current_user: dict = Depends(get_current_user),
):
    """
    Returns all active jobs, joined with the employer's name.

    use_preferences=True (default): if the caller is a seeker with saved
    preferences, results are filtered to matching categories/keywords —
    mirrors the seeker dashboard automatically applying saved preferences.

    use_preferences=False: returns the full unfiltered job board —
    mirrors the seeker clicking "Browse Jobs" without filters applied.
    """
    categories = None
    keywords = None

    if use_preferences and current_user["role"] == "seeker":
        prefs = await db.get
