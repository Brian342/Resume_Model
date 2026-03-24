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