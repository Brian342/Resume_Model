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
        job_in: JobCreated,
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
        prefs = await db.get_seeker_preferences(current_user["id"])
        if prefs["categories"]:
            categories = ", ".join(prefs["categories"])
        if prefs["keywords"]:
            keywords = ", ".join(prefs["keywords"])

    jobs = await db.get_all_active_jobs(categories=categories, keywords=keywords)
    return jobs


# LIST MY JOBS  — mirrors get_jobs_by_employer() on employer_dashboard.py
@router.get(
    "/mine",
    response_model=list[JobOut],
    summary="View all jobs posted by the logged-in employer",
)
async def list_my_jobs(current_user: dict = Depends(require_employer)):
    """
    Returns every job posted by this employer, active or not —
    this is the employer's own management view, so inactive
    (paused) listings are included unlike the public job board.
    """
    jobs = await db.get_jobs_by_employer(current_user["id"])
    return jobs


# GET ONE JOB  — mirrors the job detail page
@router.get(
    "/{job_id}",
    response_model=JobOut,
    summary="View a single job's full detail page",
)
async def get_job(
        job_id: int,
        current_user: dict = Depends(get_current_user),
):
    """Returns full details for one job. Open to any logged-in user."""
    job = await db.get_job_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return job


# UPDATE  — mirrors update_job() called from employer_dashboard.py
@router.patch(
    "/{job_id}",
    response_model=MessageResponse,
    summary="Edit an existing job listing (owner only)",
)
async def edit_job(
        job_id: int,
        job_in: JobUpdate,
        current_user: dict = Depends(require_employer),
):
    """
        Updates a job's fields. Only fields provided in the request body
        are changed — anything omitted keeps its current value.
        Only the employer who posted the job can edit it.
        """
    existing = await _get_owned_job_or_404(job_id, current_user["id"])
    # Merge: use new value if provided, otherwise keep the existing one.
    # This mirrors how employer_dashboard.py pre-fills the edit form
    # with current values and only changes what the employer edits.
    await db.update_job(
        job_id=job_id,
        title=job_in.title if job_in.title is not None else existing["title"],
        company=job_in.company if job_in.company is not None else existing["company"],
        location=job_in.location if job_in.location is not None else existing["location"],
        description=job_in.description if job_in.description is not None else existing["description"],
        requirements=job_in.requirements if job_in.requirements is not None else existing["requirements"],
        salary=job_in.salary if job_in.salary is not None else existing["salary"],
    )

    # is_active is handled separately since update_job() doesn't touch it
    if job_in.is_active is not None:
        await db.toggle_job_active(job_id, job_in.is_active)

    return MessageResponse(message="Job updated successfully")

# TOGGLE ACTIVE  — mirrors toggle_job_active() called from employer_dashboard.py
@router.patch(
    "/{job_id}/toggle",
    response_model=MessageResponse,
    summary="Activate or deactivate a job listing (owner only)",
)
async def toggle_job(
        job_id: int,
        is_active: bool,
        current_user: dict = Depends(require_employer),
):
    """
        Pauses or re-activates a listing without deleting it.
        Mirrors the "Pause" / "Activate" buttons on the employer dashboard.
        """
    await _get_owned_job_or_404(job_id, current_user["id"])

    await db.toggle_job_active(job_id, is_active)

    state = "activated" if is_active else "paused"
    return MessageResponse(message=f"Job {state} successfully")

# DELETE  — mirrors delete_job() called from employer_dashboard.py
@router.delete(
    "/{job_id}",
    response_model=MessageResponse,
    summary="Permanently delete a job and its applications (owner only)",
)
async def remove_job(
        job_id: int,
        current_user: dict = Depends(require_employer),
):
    """
        Permanently deletes a job and all applications tied to it.
        This is destructive and irreversible — the frontend should
        confirm with the employer before calling this, exactly like
        the confirmation step in employer_dashboard.py.
        """
    await _get_owned_job_or_404(job_id, current_user["id"])

    await db.delete_job(job_id)

    return MessageResponse(message="Job and its applications were deleted.")




