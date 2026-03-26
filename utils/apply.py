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

    WHEN YOU ARE READY TO ADD ML:
        1. Replace the two lines below with your model's prediction
        2. The rest of the system already handles the score - nothing
            else needs to change.
    """
    #
