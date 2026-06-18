"""
routers/applications.py — Apply, Score, Review Applications
================================================================
This is the REST equivalent of apply.py (seeker submitting an application)
and the "My Applications" tab in seeker_dashboard.py, plus the applicant
review side of employer_dashboard.py.

ENDPOINTS:
  POST   /applications                  → seeker submits an application
                                            (resume upload + screening answers +
                                            automatic ML scoring, all in one step
                                            — mirrors show_application_form()'s
                                            submit handler exactly)
  GET    /applications/mine             → seeker's "My Applications" tab
  GET    /applications/mine/stats       → seeker's Overview tab metric cards
  GET    /applications/job/{job_id}     → employer reviews applicants for one job
  PATCH  /applications/{id}/status      → employer approves/rejects an application
  GET    /applications/{id}/questions   → fetch the 5 tailored interview questions
                                            for a job (mirrors the question bank
                                            + category detection logic)

WHY SCORING HAPPENS INLINE (not a separate endpoint):
  The original apply.py scores the resume the moment the seeker submits —
  there's no separate "scoring step" the user triggers. To keep behavior
  identical, this router does the same: upload → parse → save → score →
  write score back, all within the single POST /applications call.
"""

import json
import random
import joblib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from .. import db
from ..auth_utils import get_current_user, require_employer, require_seeker
from ..models import ApplicationOut, ApplicationStatusUpdate, MessageResponse

router = APIRouter(prefix="/applications", tags=["Applications"])

# ML MODEL LOADING  (mirrors the top of apply.py)
_MODEL_PATH = Path(__file__).parent.parent / "resume_model.pkl"

try:
    _model_bundle = joblib.load(_MODEL_PATH)
    MODEL_LOADED = True
except FileNotFoundError:
    _model_bundle = None
    MODEL_LOADED = False

# Resume storage folder — same convention as the original UPLOAD_DIR
UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "resume"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# QUESTION BANK  (mirrors apply.py's QUESTION_BANK + _detect_job_category)
# Trimmed to the same 9 categories; each list kept short here for
# readability — paste your full 10-question lists back in from apply.py,
# the structure and keys are identical.
QUESTION_BANK = {
    "software": [
        "Describe a challenging bug you encountered and how you debugged and resolved it.",
        "Explain the difference between object-oriented and functional programming with examples from your experience.",
        "How do you ensure code quality and maintainability on a team project?",
        "Walk us through how you would design a RESTful API for a simple e-commerce platform.",
        "What is your approach to version control and branching strategies in a collaborative codebase?",
        "Describe a time you had to refactor a large codebase. What was your process?",
        "How do you stay current with new programming languages, frameworks, and best practices?",
        "Explain the concept of CI/CD and how you have implemented or worked within a pipeline.",
        "What testing strategies do you use and why? (unit, integration, end-to-end)",
        "Describe a project where you had to optimise for performance. What bottlenecks did you find?",
    ],
    "data": [
        "Describe a data pipeline you have built from ingestion to visualisation.",
        "How do you validate the quality and integrity of a dataset before modelling?",
        "Explain a machine learning project you worked on end-to-end.",
        "How do you communicate technical findings to non-technical stakeholders?",
        "Describe your experience with SQL and any large-scale data warehousing tools.",
        "What is your process for feature engineering and selection?",
        "How do you handle imbalanced datasets in a classification problem?",
        "Describe a time your analysis changed a business decision.",
        "What tools do you use for data visualisation and why?",
        "How do you approach model evaluation and avoiding overfitting?",
    ],
    "hr": [
        "Describe how you have managed a full-cycle recruitment process.",
        "How do you handle a conflict between an employee and their manager?",
        "What is your approach to building an inclusive hiring pipeline?",
        "Describe your experience with HR information systems (HRIS).",
        "How do you measure the success of an onboarding programme?",
        "Describe a time you had to deliver difficult news to an employee.",
        "How do you stay current with employment law and compliance changes?",
        "What strategies have you used to improve employee retention?",
        "Describe your approach to performance review cycles.",
        "How do you handle confidential employee information?",
    ],
    "finance": [
        "Describe your experience preparing financial statements or reports.",
        "How do you approach variance analysis in a budgeting process?",
        "Describe a time you identified a costly financial error. How did you resolve it?",
        "What accounting or ERP software are you most proficient in?",
        "How do you ensure compliance with relevant financial regulations?",
        "Describe your experience with forecasting or financial modelling.",
        "How do you prioritise tasks during month-end or year-end close?",
        "Describe a time you had to explain complex financial data to a non-finance audience.",
        "What is your experience with audits, internal or external?",
        "How do you approach risk assessment in financial decision-making?",
    ],
    "marketing": [
        "Describe a marketing campaign you led from strategy to execution.",
        "How do you measure ROI on a marketing campaign?",
        "Describe a time a campaign underperformed. How did you diagnose the problem and pivot?",
        "What CRM tools have you worked with and how have you used data to personalise outreach?",
        "How do you approach content strategy for thought leadership?",
        "Describe your experience managing a marketing budget and allocating spend across channels.",
        "How do you balance short-term performance marketing goals with long-term brand building?",
    ],
    "operations": [
        "Describe a process improvement initiative you led and the measurable impact it had.",
        "How do you prioritise competing operational tasks when resources are constrained?",
        "Describe your experience with project management methodologies (Agile, PMP, PRINCE2, etc.).",
        "How do you build relationships with suppliers and manage vendor performance?",
        "Describe a time a key operational process failed. What was your response?",
        "How have you used data or KPIs to drive operational decisions?",
        "What is your experience managing cross-functional teams or projects?",
        "Describe how you have managed change within an organisation.",
        "How do you approach risk management in a complex operational environment?",
        "What tools do you use for project tracking, reporting, and team collaboration?",
    ],
    "design": [
        "Walk us through your design process from brief to final delivery.",
        "How do you incorporate user research and feedback into your design decisions?",
        "Describe a project where you had to balance aesthetics with technical or business constraints.",
        "How do you handle feedback or critique from stakeholders who want changes you disagree with?",
        "What design tools and prototyping software are you most proficient in?",
        "Describe your experience with design systems or component libraries.",
        "How do you ensure accessibility standards are met in your designs?",
        "Describe a time you had to design under a very tight deadline. How did you manage it?",
        "How do you approach responsive design across different device sizes?",
        "What is your process for handing off designs to developers and ensuring accurate implementation?",
    ],
    "cybersecurity": [
        "Describe your experience conducting a vulnerability assessment or penetration test.",
        "How do you stay current with emerging threats and CVEs?",
        "Describe a time you responded to a security incident. What was your process?",
        "What SIEM or monitoring tools have you used?",
        "How do you approach security awareness training for non-technical staff?",
    ],
    "networking": [
        "Describe your experience designing or maintaining enterprise network infrastructure.",
        "How do you troubleshoot intermittent connectivity issues across a large network?",
        "What is your experience with cloud networking (AWS/Azure/GCP)?",
        "Describe your approach to network security and segmentation.",
        "How do you document and maintain network topology changes?",
    ],
    "general": [
        "Tell us about a professional achievement you are most proud of and why.",
        "Describe a situation where you had to learn a new skill quickly under pressure.",
        "How do you manage competing priorities and deadlines?",
        "Describe a time you had a conflict with a colleague. How did you resolve it?",
        "What does success look like to you in this role after the first 90 days?",
        "Where do you see your career heading in the next three to five years?",
        "Describe your ideal work environment and team culture.",
        "How do you handle constructive criticism or negative feedback?",
        "Tell us about a time you went above and beyond what was expected of you.",
        "What motivates you to do your best work?",
    ],
}


def _detect_job_category(job: dict) -> str:
    """
    Maps a job's title/description to a question-bank key.
    Title is checked first (higher confidence), then full text as fallback.
    Mirrors _detect_job_category() in apply.py exactly — same keyword
    lists, same ordering (HR and Finance checked before generic "engineer"
    terms so they're never mis-classified as software roles).
    """
    title = job["title"].lower()
    full_text = (job["title"] + " " + job["description"] + " " + job["requirements"]).lower()

    title_rules = [
        ("hr", ["hr", "human resource", "human resources", "recruitment",
                "talent acquisition", "talent management", "payroll",
                "people operations", "people ops", "hrbp"]),
        ("finance", ["finance", "financial", "accounting", "accountant",
                     "audit", "auditor", "tax", "budget", "treasurer", "cfo"]),
        ("marketing", ["marketing", "brand", "seo", "digital marketing",
                       "content", "campaign", "crm", "growth"]),
        ("cybersecurity", ["security", "cyber", "penetration", "soc", "siem", "ethical hack"]),
        ("networking", ["network", "networking", "infrastructure", "cisco",
                        "devops", "cloud engineer", "systems admin", "sysadmin", "network admin"]),
        ("data", ["data scientist", "machine learning", "data analyst",
                  "nlp", "deep learning", "data engineer", "bi analyst", "analytics"]),
        ("software", ["software", "developer", "programmer", "web developer",
                      "mobile", "backend", "frontend", "full stack", "fullstack"]),
        ("operations", ["operations", "project manager", "supply chain",
                        "logistics", "procurement", "operations manager"]),
        ("design", ["design", "designer", "ui", "ux", "graphic", "figma",
                    "creative", "illustrator"]),
    ]
    for category, words in title_rules:
        if any(w in title for w in words):
            return category

    fulltext_rules = [
        ("hr", ["human resource", "hr manager", "hr officer", "recruitment",
                "talent acquisition", "payroll", "people operations"]),
        ("finance", ["finance", "accounting", "audit", "financial analyst",
                     "tax", "budget", "treasurer"]),
        ("marketing", ["marketing", "brand", "seo", "digital marketing",
                       "content strategy", "campaign", "crm"]),
        ("cybersecurity", ["security", "cyber", "penetration", "soc ", "siem", "ethical hack"]),
        ("networking", ["network admin", "network engineer", "infrastructure",
                        "cisco", "devops", "cloud engineer", "systems admin", "sysadmin"]),
        ("data", ["data scientist", "machine learning", "data analyst",
                  "nlp", "deep learning", "data engineer", "bi ", "analytics"]),
        ("software", ["software engineer", "software developer", "backend developer",
                      "frontend developer", "full stack", "mobile developer"]),
        ("operations", ["operations manager", "project manager", "supply chain",
                        "logistics", "procurement"]),
        ("design", ["ux designer", "ui designer", "graphic designer", "figma", "creative director"]),
    ]
    for category, words in fulltext_rules:
        if any(w in full_text for w in words):
            return category

    return "general"


# RESUME PARSING + SCORING  (mirrors score_resume + extract_text_from_pdf in apply.py)

def _save_resume_bytes(file_bytes: bytes, filename: str, seeker_id: int, job_id: int) -> str:
    """Saves uploaded resume bytes to disk. Mirrors save_resume() in apply.py.
    """
    safe_name = f"seeker{seeker_id}_job{job_id}_{filename}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return str(file_path)


def score_resume(parsed_resume: dict, job: Optional[dict] = None) -> tuple:
    """
    Scores a resume against a specific job.
    Identical formula to apply.py's score_resume():
        final_score = (ml_score * 0.4) + (overlap_score * 100 * 0.6)
    Falls back to ml_score alone if no job context is given.
    Returns (final_score: float, label: str, matched_skills: list, missing_skills: list).
    """
    from ..resume_parser import extract_job_skills, compute_skill_overlap

    if not MODEL_LOADED or _model_bundle is None:
        skills_count = parsed_resume.get("skill_count", 0)
        exp_years = parsed_resume.get("experience_years", 0)
        ml_score = min(100, skills_count * 8 + exp_years * 5)
    else:
        resume_data = {
            "skills": parsed_resume["skills"],
            "experience_years": parsed_resume["experience_years"],
            "education": parsed_resume["education"],
            "certifications": parsed_resume["certifications"],
            "job_role": parsed_resume["job_role"],
            "projects_count": parsed_resume["projects_count"],
            "Education": parsed_resume["education"],
            "Certifications": parsed_resume["certifications"],
            "Job Role": parsed_resume["job_role"],
        }
        try:
            from ..train_model import predict_single
            ml_score, _ = predict_single(_model_bundle, resume_data)
        except Exception:
            ml_score = .0

    matched_skills, missing_skills = [], []
    if job is not None:
        job_skills = extract_job_skills(job["description"], job["requirements"])
        resume_skills = parsed_resume.get("skills_list", [])
        overlap = compute_skill_overlap(resume_skills, job_skills)

        matched_skills = list(
            set(s.lower() for s in resume_skills) & set(s.lower() for s in job_skills)
        )
        missing_skills = list(
            set(s.lower() for s in job_skills) - set(s.lower() for s in resume_skills)
        )

        final_score = round((ml_score * .4) + (overlap * 100 * .6), 1)
    else:
        final_score = round(ml_score, 1)

    if final_score >= 65:
        label = "Qualified"
    elif final_score >= 40:
        label = "Review Needed"
    else:
        label = "Not Qualified"

    return float(final_score), label, matched_skills, missing_skills


# SUBMIT APPLICATION  — mirrors show_application_form()'s submit handler
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Submit an application: upload resume, answer questions, get scored",
)
async def submit_application(
        job_id: int = Form(...),
        why_interested: str = Form(...),
        relevant_experience: str = Form(...),
        years_experience: str = Form(...),
        availability: str = Form(...),
        interview_answers: str = Form("{}"),
        resume: Optional[UploadFile] = File(None),
        current_user: dict = Depends(require_seeker),
):
    """
        Full submission flow, mirroring show_application_form()'s submit_clicked block:
          1. Validate the job exists
          2. Save the uploaded resume (if provided)
          3. Parse the resume text
          4. Save the application + answers as a JSON blob
          5. Score the resume against the job (40% ML quality + 60% skill overlap)
          6. Write the score back onto the application
          7. Return the score + matched/missing skills, just like show_success_screen()

        interview_answers is a JSON string the client builds from the 5 tailored
        questions returned by GET /applications/{job_id}/questions.
        """
    job = await db.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not Found.")

    if not why_interested.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please answer: Why are you interested in this role?")

    if not relevant_experience.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please describe your most relevant experience.")

    seeker_id = current_user["id"]

    # ── Save + parse resume ──
    # parse_resume() does its own PDF text extraction internally (pdfplumber,
    # falling back to PyPDF2) — it expects a file-like object, not raw text.
    parsed_resume = None
    resume_path = ""
    if resume is not None:
        file_bytes = await resume.read()
        resume_path = _save_resume_bytes(file_bytes, resume.filename, seeker_id, job_id)

        from ..resume_parser import parse_resume
        from io import BytesIO
        parsed_resume = parsed_resume(BytesIO(file_bytes))
        if not parsed_resume.get("raw_text"):
            parsed_resume = None

    try:
        ai_answer = json.loads(interview_answers)
    except json.JSONDecodeError:
        ai_answer = {}

    answers = {
        "Why interested in this role?": why_interested.strip(),
        "Most relevant experience": relevant_experience.strip(),
        "Years of experience": years_experience,
        "Availability to start": availability,
        **ai_answer
    }
    answers_json = json.dumps(answers)

    saved = await db.create_application(
        job_id=job_id,
        seeker_id=seeker_id,
        resume_path=resume_path,
        answers_json=answers_json,
    )
    if not saved:
        raise HTTPException(status.HTTP_409_CONFLICT, "you have already applied to this job")

    if parsed_resume:
        score, label, matched_skills, missing_skills = score_resume(parsed_resume, job=job)
    else:
        score, label, matched_skills, missing_skills = .0, "No resume data", [], []

    all_apps = await db.get_applications_by_seeker(seeker_id)
    latest_app = next((a for a in all_apps if a["job_id"] == job_id), None)
    if latest_app:
        await db.update_application_score(latest_app["id"], score, label)

    return {
        "message": "Application submitted successfully.",
        "ai_score": score,
        "ml_label": label,
        "matched_skills": matched_skills[:6],
        "missing_skills": missing_skills[:6],
    }


# INTERVIEW QUESTIONS  — mirrors the question-selection block in apply.py
@router.get(
    "/questions/{job_id}",
    summary="Get 5 tailored interview questions for a job",
)
async def get_interview_questions(
        job_id: int,
        current_user: dict = Depends(require_seeker),
):
    """
    Returns the 5 category-tailored questions for this job.
    Uses job_id as the random seed so the same job always returns
    the same 5 questions, exactly like the original (rng = random.Random(job["id"])).
    """
    job = await db.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")

    category_key = _detect_job_category(job)
    category_pool = QUESTION_BANK.get(category_key, []) or QUESTION_BANK["general"]

    rng = random.Random(job_id)
    selected_questions = rng.sample(category_pool, min(s, len(category_pool)))

    return {
        "job_id": job_id,
        "category": category_key,
        "questions": selected_questions,
    }


# MY APPLICATIONS  — mirrors show_my_applications_tab()
@router.get(
    "/mine",
    response_model=list[ApplicationOut],
    summary="List all applications submitted by the logged-in seeker",
)
async def list_my_applications(
        status_filter: Optional[str] = None,
        current_user: dict = Depends(require_seeker),
):
    """
        Returns the seeker's applications, joined with job title/company/location.
        status_filter: 'pending' | 'approved' | 'rejected' (omit for all) —
        mirrors the filter_status selectbox in show_my_applications_tab().
        """
    apps = await db.get_applications_by_seeker(current_user["id"])

    if status_filter:
        apps = [a for a in apps if a["status"] == status_filter.lower()]

    return apps


# MY STATS  — mirrors show_overview_tab()'s metric cards
@router.get(
    "/mine/stats",
    summary="Get application stat counts for the Overview tab",
)
async def my_application_stats(current_user: dict = Depends(require_seeker)):
    """
    Returns { total_applied, qualified, pending, rejected } —
    powers the four metric cards on the seeker's Overview tab.
    """
    return await db.get_seeker_stats(current_user["id"])


@router.get(
    "/job/{job_id}",
    response_model=list[ApplicationOut],
    summary="View all applicants for a job (owner only)",
)
async def list_applicants_for_job(
        job_id: int,
        current_user: dict = Depends(require_employer),
):
    """
        Returns applicants for a job, sorted by ai_score DESC (unscored last),
        joined with seeker name + email. Only the employer who owns the job
        can view its applicants.
        """
    job = await db.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")

    if job["employer_id"] != current_user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view applicants for your own Jobs.")

    return await db.get_applications_by_job(job_id)


@router.get(
    "/{application_id}/resume",
    summary="Download an applicant's resume PDF (employer, job owner only)",
)
async def download_resume(
        application_id: int,
        current_user: dict = Depends(require_employer),
):
    """
        Streams the applicant's uploaded resume file.
        Mirrors show_resume_download() in employer_dashboard.py.
        Only the employer who owns the underlying job can download it.
        """
    from fastapi.responses import FileResponse

    app = await db.get_applications_by_id(application_id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")

    job = await db.get_job_by_id(app["job_id"])
    if job is None or job["employer_id"] != current_user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view applicants for your own jobs.")

    resume_path = app.get("resume_path")
    if not resume_path or not Path(resume_path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume file was uploaded for this application.")

    return FileResponse(
        path=resume_path,
        media_type="application/pdf",
        filename=Path(resume_path).name,
    )
# EMPLOYER: APPROVE / REJECT
@router.patch(
    "/{application_id}/status",
    summary="Approve or reject an applicant (employer, job owner only)",
)
async def update_status(
        application_id: int,
        body: ApplicationStatusUpdate,
        current_user: dict = Depends(require_employer),
):
    """
        Updates an application's status and, on approve/reject, sends the
        candidate a notification email — mirrors employer_dashboard.py's
        Approve/Reject button handlers exactly, including "approved but
        email failed" being a non-fatal warning rather than an error.
        """
    app = await db.get_application_by_id(application_id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not Found.")

    job = await db.get_job_by_id(app["job_id"])
    if job is None or job["employer_id"] != current_user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only review applicants for your own jobs.")

    await db.update_application_status(application_id, body.status.value)

    seeker = await db.get_user_by_id(app["seeker_id"])
    email_sent = False
    email_message = "Email not configured."

    if seeker and body.status.value in ("approved", "rejected"):
        try:
            from ..email_utils import send_approval_email, send_rejection_email

            sender = send_approval_email if body.status.value == "approved" else send_rejection_email

            email_sent, email_message = sender(
                to_email=seeker["email"],
                to_name=seeker["full_name"],
                job_title=job["title"],
                company=job["company"],
            )
        except Exception as e:
            email_message = f"Email failed: {e}"

    return {
        "message": f"Application marked as {body.status.value}.",
        "email_sent": email_sent,
        "email_message": email_message,
    }

