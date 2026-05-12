"""
employer_dashboard.py — Employer Section
=========================================
This file contains ONE function: show_employer_dashboard()
It is imported and called from app.py inside the main() router.

It has three tabs:
  Tab 1 — Overview   : metrics + list of their posted jobs
  Tab 2 — Post a Job : form to create a new job listing
  Tab 3 — Applicants : review applicants, approve or reject, send email

IMPORTS USED:
  db.py functions — all databases read/write
  email_utils.py — sending approval/rejection emails (we build this next)
  streamlit — all UI components
  json             — to decode the answers stored as JSON in the DB
"""
import os.path

import streamlit as st
import json
from db import (
    create_job,
    get_jobs_by_employer,
    get_applications_by_job,
    update_application_status,
    toggle_job_active,
    delete_job,
    update_job
)

try:
    from email_utils import send_approval_email, send_rejection_email

    EMAIL_READY = True
except ImportError:
    EMAIL_READY = False


# Helper - Score Colour
def score_color(score):
    """
    Returns a colour hex based on the AI score Value.
    Used to colour-code scores in the applicant table.
    Green -> 70 and above (strong Match)
    Orange -> 40 to 69 (possible match)
    Red -> below 40 (weak match)
    """
    if score is None:
        return "#888888"  # grey - not scored yet
    if score >= 70:
        return "#2e7d32"  # green
    if score >= 40:
        return "#e65100"  # orange
    return "#c62828"  # red


# HELPER RESUME DOWNLOAD BUTTON
def show_resume_download(resume_path: str, seeker_name: str, app_id: int = None):
    """
    Reads the resume PDF from disk and renders a Streamlit
    download button so the employer can download it directly.

    resume_path : the file path stored in the database
    seeker_name : used to name the downloaded file nicely
    """
    if not resume_path:
        st.caption("No resume uploaded")
        return

    if not os.path.exists(resume_path):
        st.caption(f"Resume file not found on server")
        return

    try:
        with open(resume_path, "rb") as f:
            pdf_bytes = f.read()

        # Clean the seeker name for use as a filename
        safe_name = seeker_name.replace(" ", "_").lower()
        filename = f"resume_{safe_name}.pdf"

        # Use app_id for a guaranteed-unique key: fail back to path bash if not provided
        unique_key = f"dl_{app_id}" if app_id is not None else f"dl_{abs(hash(resume_path))}"
        st.download_button(
            label="Download Resume",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
            key=unique_key  # Unique key per file
        )
    except Exception as e:
        st.caption(f"Could not load resume: {e}")


# Tab 1 overview
def show_overview_tab(employer_id):
    """
    Shows summary metrics and a list of the employer's job postings.
    employer_id: the logged-in employer's user ID from session_state
    """
    jobs = get_jobs_by_employer(employer_id)

    # Metric cards
    # Count total applicants across all jobs by summing up applications per job
    total_applicants = 0
    pending_count = 0

    for job in jobs:
        apps = get_applications_by_job(job["id"])
        total_applicants += len(apps)
        pending_count += sum(1 for a in apps if a["status"] == "pending")

    # st.columns creates a row of equal-width columns
    # st.metric shows a big number with a label - perfect for dashboards
    col1, col2, col3 = st.columns(3)
    col1.metric("Jobs Posted", len(jobs))
    col2.metric("Total Applicants", total_applicants)
    col3.metric("Pending Reviews", pending_count)

    st.divider()

    # Job Listings Table
    st.markdown("### Your Job Listings")

    if not jobs:
        st.info("You haven't posted any jobs yet. Go to the **Post a Job** tab to get started.")
        return

    # Edit form (shown above the list when editing)
    # We store the job being edited in session_state["editing_job_id"]
    # When set, we show the edit form at the top of this tab.
    if st.session_state.get("editing_job_id"):
        show_edit_job_form(employer_id)
        st.divider()

    for job in jobs:
        # st.expander creates a collapsible section
        # The label shows the job title and its active/paused status
        status_badge = "Active" if job["is_active"] else "Paused"
        apps = get_applications_by_job(job["id"])

        with st.expander(f"{job['title']} - {job['company']} | {status_badge} | {len(apps)} applicant(s)"):

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Location:** {job['location']}")
                st.markdown(f"**Salary:** {job['salary'] or 'Not specified'}")
                st.markdown(f"**Posted:** {str(job['created_at'])[:10]}")
                st.markdown(f"**Applicants:** {len(apps)}")

            with col2:
                # Toggle active/paused - lets employer hide a job without deleting it
                if job["is_active"]:
                    if st.button("Paused listing", key=f"Pause_{job['id']}", use_container_width=True):
                        toggle_job_active(job["id"], 0)
                        st.success("Job Paused.")
                        st.rerun()
                else:
                    if st.button("Re-activate", key=f"active_{job['id']}", use_container_width=True):
                        toggle_job_active(job["id"], 1)
                        st.success("Job re-activated.")
                        st.rerun()

                # Edit Button
                if st.button("Edit", key=f"edit_{job['id']}", use_container_width=True):
                    st.session_state["editing_job_id"] = job["id"]
                    st.session_state["editing_job_data"] = dict(job)
                    st.rerun()

                # Delete button
                # 2-step: first click set a flag, second click confirms
                delete_key = f"confirm_delete_{job['id']}"

                if st.session_state.get(delete_key):
                    # Confirmation step - shown after first click
                    st.warning("Are you sure? This deletes the job and All applications!!.")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, Delete", key=f"yes_{job['id']}", type="primary", use_container_width=True):
                            delete_job(job["id"])
                            st.session_state.pop(delete_key, None)
                            st.success("job deleted.")
                            st.rerun()
                    with col_no:
                        if st.button("Cancel", key=f"no_{job['id']}", use_container_width=True):
                            st.session_state.pop(delete_key, None)
                            st.rerun()
                else:
                    if st.button("Delete", key=f"delete_{job['id']}", use_container_width=True):
                        # First click - set confirmation flag
                        st.session_state[delete_key] = True
                        st.rerun()


# Edit Job Form
def show_edit_job_form(employer_id):
    """
    Shows a pre-filled form to edit an existing job.
    Triggered when employer clicks Edit on a job card.

    The form is pre-filled with the job's current values from
    session_state["editing_job_data"] so the employer can see
    what is already there and only change what they want.
    """
    job_data = st.session_state.get("editing_job_data", {})

    st.markdown("### Edit Job Posting")

    with st.form("edit_job_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Job Title *", value=job_data.get("title", ""))
            company = st.text_input("Company Name *", value=job_data.get("company", ""))

        with col2:
            location = st.text_input("Location *", value=job_data.get("location", ""))
            salary = st.text_input("Salary/Range", value=job_data.get("salary", "") or "")

            description = st.text_area(
                "Job Description *",
                value=job_data.get("description", ""),
                height=160
            )
            requirements = st.text_area(
                "Requirements *",
                value=job_data.get("requirements", ""),
                height=130
            )

            col_save, col_cancel = st.columns(2)
            with col_save:
                save = st.form_submit_button(
                    "Save Changes", type="primary", use_container_width=True
                )
            with col_cancel:
                cancel = st.form_submit_button(
                    "Cancel", use_container_width=True
                )
    if save:
        if not all([title, company, location, description, requirements]):
            st.error("Please fill in all required fields.")
        else:
            update_job(
                job_id=st.session_state["editing_job_id"],
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                description=description.strip(),
                requirements=requirements.strip(),
                salary=salary.strip()
            )
            st.session_state.pop("editing_job_id", None)
            st.session_state.pop("editing_job_data", None)
            st.success("Job updated successfully!")
            st.rerun()
    if cancel:
        st.session_state.pop("editing_job_id", None)
        st.session_state.pop("editing_job_data", None)
        st.rerun()


# Tab 2 Post A job
def show_post_job_tab(employer_id):
    """
    A form for the employer to create a new job listing.
    On submit.It calls create_job() from db.py and saves to the database.
    """
    st.markdown("### Post a New Job")
    st.markdown("Fill in the details below. All fields marked \\* are required.")

    # st.form groups widgets together so Streamlit only re-runs
    # When the submit button is clicked - not on every keystroke
    # This is important for forms with many fields

    with st.form("post_job_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Job Title *", placeholder="e.g. Data Analyst")
            company = st.text_input("Company Name *", placeholder="e.g. Pioneer Insurance Group")

        with col2:
            location = st.text_input("Location *", placeholder="e.g. Nairobi, Kenya / Remote")
            salary = st.text_input("Salary / Range", placeholder="e.g. KES 80,000 - 120,000")

        st.markdown("----")

        description = st.text_area(
            "Job Description *",
            placeholder="Describe the role, Responsibilities, team and Work Environment...",
            height=180
        )

        requirements = st.text_area(
            "Requirements *",
            placeholder="List the skills, qualifications and experience needed...\n"
                        "e.g.\n- Bachelor's degree in Computer Science\n- 2+ years Python experience",
            height=150
        )

        # st.form_submit_button only works inside st.form
        # type="Primary" makes it the blue/highlighted button

        submitted = st.form_submit_button("Post Job", type="primary", use_container_width=True)

        # Handle submission
        # This runs AFTER form block - important: Logic goes outside the form
    if submitted:
        # Validate required fields
        if not all([title, company, location, description, requirements]):
            st.error("Please fill in all required fields marked with *")
        else:
            job_id = create_job(
                employer_id=employer_id,
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                description=description.strip(),
                requirements=requirements.strip(),
                salary=salary.strip()
            )

            st.success(f"Job Posted Successfully: Job ID #{job_id}")
            st.balloons()


# TAB 3 Applicants
def show_applicants_tab(employer_id):
    """
    Lets the employer:
        1. Select one of their jobs from a dropdown
        2. See all applicants for that job with their AI score
        3. Expand each applicant to read their resume answers
        4. Approve or Reject - which triggers an email
    """
    st.markdown("### Review Applicants")

    jobs = get_jobs_by_employer(employer_id)

    if not jobs:
        st.info("Post a job first before reviewing applicants.")
        return

    # Build a dict mapping "Job Title (ID)" -> job_id for the selectbox
    # This gives the employer a readable label while we track the real ID
    job_options = {f"{j['title']} - {j['company']}": j["id"] for j in jobs}

    selected_label = st.selectbox(
        "Select a job to review",
        options=list(job_options.keys())
    )
    selected_job_id = job_options[selected_label]

    # Fetch all applications for the selected job
    applications = get_applications_by_job(selected_job_id)

    if not applications:
        st.info("No applications yet for this job.")
        return

    # Summary Bar
    total = len(applications)
    approved = sum(1 for a in applications if a["status"] == "approved")
    rejected = sum(1 for a in applications if a["status"] == "rejected")
    pending = sum(1 for a in applications if a["status"] == "pending")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Pending", pending)
    c3.metric("Approved", approved)
    c4.metric("Rejected", rejected)

    st.divider()

    # Applicant cards
    # Applications come back sorted by ai_score DESC from db.py
    # so the best matches apper at the top automatically.

    for app in applications:
        seeker_name = app["seeker_name"]
        seeker_email = app["seeker_email"]
        ai_score = app["ai_score"]
        ml_label = app["ml_label"] or "Not scored yet"
        status = app["status"]
        app_id = app["id"]
        resume_path = app["resume_path"]

        # score display - coloured number
        score_display = f"{ai_score:.0f}/100" if ai_score is not None else "Pending"
        color = score_color(ai_score)

        # status
        status_icon = {"pending": "🕐", "approved": "✅", "rejected": "❌"}.get(status, "")

        with st.expander(
                f"{status_icon} {seeker_name} | Score: {score_display} | {ml_label}"
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Email:** {seeker_email}")
                st.markdown(f"** Applied:** {str(app['applied_at'])[:10]}")
                st.markdown(f"**status:** `{status.upper()}`")

                # show AI score as a coloured progress bar
                if ai_score is not None:
                    st.markdown(f"**AI Match Score:**")
                    st.markdown(
                        f"<div style='background:#e0e0e0;border-radius:8px;height:16px;width:100%'>"
                        f"<div style='background:{color};width:{ai_score}%;height:16px;"
                        f"border-radius:8px;'></div></div>"
                        f"<p style='color:{color};font-weight:600;margin-top:4px'>"
                        f"{ai_score:.0f} / 100 — {ml_label}</p>",
                        unsafe_allow_html=True
                    )

                # Parse and display screening question answers
                if app["answers"]:
                    st.markdown("**Screening answers:**")
                    try:
                        answers = json.loads(app["answers"])
                        for question, answer in answers.items():
                            st.markdown(f"- **{question}:** {answer}")
                    except (json.JSONDecodeError, TypeError):
                        st.markdown(f"_{app['answers']}_")

            with col2:
                st.markdown("**Resume**")
                show_resume_download(resume_path, seeker_name)

                st.divider()

                st.markdown("**Decision**")

                # Only show action buttons if still pending
                # Once a decision is made the buttons are replaced by a label
                if status == "pending":
                    if st.button(
                            "Approve",
                            key=f"approve_{app_id}",
                            use_container_width=True,
                            type="primary"
                    ):
                        update_application_status(app_id, "approved")
                        st.success("Application Approved")

                        # Send Congratulation email
                        if EMAIL_READY:
                            matched = [j for j in jobs if j["id"] == selected_job_id]
                            if matched:
                                job = matched[0]
                                email_success, msg = send_approval_email(
                                    to_email=seeker_email,
                                    to_name=seeker_name,
                                    job_title=job["title"],
                                    company=job["company"]
                                )
                            if email_success:
                                st.info(f"Congratulations email sent to {seeker_email}")
                            else:
                                st.warning(f"Approved but Email Failed: {msg}")
                        else:
                            st.info("Email not configured yet - approval Saved")

                        st.rerun()

                    if st.button(
                            "Reject",
                            key=f"reject_{app_id}",
                            use_container_width=True
                    ):
                        update_application_status(app_id, "rejected")
                        st.warning("Application rejected")

                        # Send Rejection email
                        if EMAIL_READY:
                            matched = [j for j in jobs if j["id"] == selected_job_id]
                            if matched:
                                job = matched[0]
                                email_success, msg = send_rejection_email(
                                    to_email=seeker_email,
                                    to_name=seeker_name,
                                    job_title=job["title"],
                                    company=job["company"]
                                )
                            if email_success:
                                st.info(f"Rejected. Notification sent to {seeker_email}.")
                            else:
                                st.warning(f"Rejected! but Email failed: {msg}")
                        else:
                            st.info("Email ot configured yet - rejection saved")

                        st.rerun()

                elif status == "approved":
                    st.success("Approved")
                elif status == "rejected":
                    st.error("Rejected")


# Main Function called from app.py
def show_employer_dashboard():
    """
    Enty point for this page.
    app.py calls this function when current_page == "employer_dashboard".

    It reads the employer's ID from session_state - which was set
    during login in app.py - and passes it to each tab function
    """
    employer_id = st.session_state["user_id"]

    st.title("Employer Dashboard")
    st.markdown(f"Logged in as **{st.session_state['user_name']}**")
    st.divider()

    # st.tabs returns a list of tab context managers
    # The labels apper as clickable tabs at the top of the section
    tab1, tab2, tab3 = st.tabs(["Overview", "Post a job", "Applicants"])

    with tab1:
        show_overview_tab(employer_id)

    with tab2:
        show_post_job_tab(employer_id)

    with tab3:
        show_applicants_tab(employer_id)
