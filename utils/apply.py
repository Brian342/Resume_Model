"""
apply.py - Job Details & Application page
This file contains ONE Function: show_apply_page()
It is Imported and called from app.py inside the main() router.

This page has TWO stages that render one at a time:

    STAGE 1 - Job Detail View
        Shows the full job description, requirements, salary, location.
        Has an "Apply Now" button that moves to Stage 2.

    STAGE 2 - Application Form
        - Resume upload (PDF)
        - 4 Screening questions the seeker must answer
        - AI interview question placeholder
        - Submit button that:
            1. Saves the resume file to disk
            2. Saves the application + answers to the database
            3. Calls your ML scorer placeholder
            4. Shows a confirmation screen

SESSION STATE KEYS USED:
    selected_job_id -> set by seeker_dashboard when "View & Apply" is clicked
    apply_stage -> "detail" or "form" - controls which stage is shown
    user_id -> seeker's database ID (set during Login)
    user_name -> seeker's name (set during login)

IMPORTS USED:
    db.py - get_job_by_id.
    Create_application,
    Update_application,
    has_applied
    streamlit -> all UI components
    JSON -> encode answers dict as a string for the database
    os / pathlib -> save the uploaded resume file to disk
"""
import streamlit as st
import json
import joblib
from pathlib import Path
from db import (
    get_job_by_id,
    create_application,
    update_application_score,
    has_applied
)
from resume_parser import parse_resume

# LOAD THE TRAINED MODEL ONCE
_MODEL_PATH = Path(__file__).parent / "resume_model.pkl"

try:
    _model_bundle = joblib.load(_MODEL_PATH)
    MODEL_LOADED = True
except FileNotFoundError:
    _model_bundle = None
    MODEL_LOADED = False

# RESUME STORAGE FOLDER
UPLOAD_DIR = Path(__file__).parent / "uploads" / "resume"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# AI SCORE PLACEHOLDER
def score_resume(parsed_resume: dict) -> tuple:
    """
        Takes the parsed resume dict from resume_parser.parse_resume()
        and returns a real ML score using the trained model.

        parsed_resume: dict returned by parse_resume()
        Returns: (score: float 0-100, label: str)
    """
    if not MODEL_LOADED or _model_bundle is None:
        skills_count = parsed_resume.get("skill_count", 0)
        exp_years = parsed_resume.get("experience_years", 0)
        fallback_score = min(100, skills_count * 8 + exp_years * 5)
        fallback_label = (
            "Qualified" if fallback_score >= 65 else
            "Review Needed" if fallback_score >= 40 else
            "Not Qualified"
        )
        return float(fallback_score), f"{fallback_label} (model not loaded)"

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
        from train_model import predict_single
        score, label = predict_single(_model_bundle, resume_data)
        return float(score), label
    except Exception as e:
        return .0, f"Scoring error: {str(e)}"


# PDF Text Extractor
def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extracts plain text from an uploaded PDF file using PyPDF2.
    This text is passed to your ML scorer.

    uploaded_file: the object returned by st.file_uploader()

    Returns a string of all the text in the PDF.
    If extraction fails, returns an empty string (the app won't crash).

    INSTALL: pip install PyPDF2
    """
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        st.warning(f"Could not extract text from PDF: {e}")
        return ""


# SAVE RESUME TO DISK
def save_resume(uploaded_file, seeker_id: int, job_id: int) -> str:
    safe_name = f"seeker{seeker_id}_job{job_id}_{uploaded_file.name}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)


