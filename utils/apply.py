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
import os
from pathlib import Path
from db import (
    get_job_by_id,
    create_application,
    update_application_score,
    has_applied
)

# Resume Storage Folder
UPLOAD_DIR = Path(__file__).parent / "uploads" / "resume"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# AI SCORE PLACEHOLDER
def score_resume(resume_text: str, job_description: str, job_requirements: str):
    """
    PLACEHOLDER - Replace this with your ML model

    This function receives:
        resume_text: raw text extracted from the PDF
        job_description: the job's description from the database
        job_requirements: the job's requirements from the database

    It should return:
        score (float): 0 to 100 match score
        label (str): "Qualified", "Not Qualified", or "Review Needed"

    Returns a fixed placeholder so the rest of the
    system works end-to-end while you build the ML model.
    """
    # Replace These two Lines with model
    score = .0  # returns a float between 0 and 100
    label = "Pending ML scoring"

    return score, label


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


# Save Resume To DisK
def show_job_details(job, seeker_id: int):
    """
    Renders the full job detail page.

    Shows all job information and an "Apply Now" button.
    If the seeker has already applied, the button is replaced
    with an "Already Applied" message.

    job       : a Row object from get_job_by_id()
    seeker_id : the logged-in seeker's user ID
    """
    # Back button
    if st.button("<- Back to Jobs"):
        st.session_state["current_page"] = "seeker_dashboard"
        st.session_state.pop("selected_job_id", None)
        st.session_state.pop("apply_stage", None)
        st.rerun()

    st.divider()

    # Job header
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title(job["title"])
        st.markdown(f"### {job['company']}")

        # Info pills row
        st.markdown(
            f"**{job['location']}** &nbsp;&nbsp;"
            f"**{job['salary'] or 'Salary not specified'}** &nbsp;&nbsp;"
            f"**Posted {str(job['created_at'])[:10]}**",
            unsafe_allow_html=True
        )
    with col2:
        # check if already applied
        already = has_applied(job["id"], seeker_id)

        if already:
            st.success("You have already applied to this job")
        else:
            # This is the main call-to-action button
            # Clicking it moves to Stage 2 (the application form)
            if st.button(
                "Apply Now",
                type = "primary",
                use_container_width=True
            ):
                st.session_state["apply_stage"] = "form"
                st.rerun()
    st.divider()
