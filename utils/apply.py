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
def score_resume(parsed_resume: dict, job=None) -> tuple:
    """
        Scores a resume against a specific job.

        HOW THE COMBINED SCORE WORKS:
        ml_score      — how good the resume is in general (0-100)
        overlap_score — what % of job's required skills the resume has (0-1)

        final_score = (ml_score × 0.4) + (overlap_score × 100 × 0.6)

        The overlap is weighted 60% because job-skill match is more
        important than general resume quality for a specific role.

        If no job is provided, falls back to ml_score only.
    """
    from resume_parser import extract_job_skills, compute_skill_overlap

    # Step 1: Get the base ML Score
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
            from train_model import predict_single
            ml_score, _ = predict_single(_model_bundle, resume_data)
        except Exception as e:
            ml_score = .0

    # Step 2: Compute job-skill overlap
    if job is not None:
        job_skills = extract_job_skills(
            job["description"],
            job["requirements"]
        )
        resume_skills = parsed_resume.get("skills_list", [])
        overlap = compute_skill_overlap(resume_skills, job_skills)

        # Show which skills matched and which were missing
        # stored in session_state so the UI can display them
        matched_skills = list(
            set(s.lower() for s in resume_skills)
            .intersection(set(s.lower() for s in job_skills))
        )
        missing_skills = list(
            set(s.lower() for s in job_skills)
            - set(s.lower() for s in resume_skills)
        )
        st.session_state["matched_skills"] = matched_skills
        st.session_state["missing_skills"] = missing_skills
        st.session_state["job_skills"] = job_skills

        # Step 3: Combine ML score + overlap score
        # 40% general ML quality + 60% job-specific skill match
        final_score = round((ml_score * .4) + (overlap * 100 * .6), 1)

    else:
        # No job context - use ML score only
        final_score = round(ml_score, 1)
        overlap = None
        matched_skills = []
        missing_skills = []

    # Step 4: Assign Label
    if final_score >= 65:
        label = "Qualified"
    elif final_score >= 40:
        label = "Review Needed"
    else:
        label = "Not Qualified"

    return float(final_score), label


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


# STAGE 1 - JOB DETAIL VIEW
def show_job_details(job, seeker_id: int):
    if st.button("<- Back to Jobs"):
        st.session_state["current_page"] = "seeker_dashboard"
        st.session_state.pop("selected_job_id", None)
        st.session_state.pop("apply_stage", None)
        st.rerun()

    st.divider()
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title(job["title"])
        st.markdown(f"### {job['company']}")
        st.markdown(
            f" **{job['location']}** &nbsp;&nbsp;"
            f" **{job['salary'] or 'Salary not specified'}** &nbsp;&nbsp;"
            f" **Posted {str(job['created_at'])[:10]}**",
            unsafe_allow_html=True
        )

    with col2:
        already = has_applied(job["id"], seeker_id)
        if already:
            st.success("Already Applied")
        else:
            if st.button("Apply Now", type="primary", use_container_width=True):
                st.session_state["apply_stage"] = "form"
                st.rerun()

    st.divider()
    tab1, tab2 = st.tabs(["Job Description", "Requirements"])

    with tab1:
        st.markdown("### About the Role")
        st.markdown(job["description"].replace("\n", "\n\n"))

    with tab2:
        st.markdown("### What we're Looking For")
        st.markdown(job["requirements"].replace("\n", "\n\n"))


# STAGE 2 APPLICATION FORM
def show_application_form(job, seeker_id: int):
    if st.button("← Back to Job Details"):
        st.session_state["apply_stage"] = "detail"
        st.rerun()

    st.markdown(f"## Applying for: {job['title']}")
    st.markdown(f"**{job['company']}** · {job['location']}")
    st.divider()

    # ── SECTION 1: Resume Upload ─────────────────────────────────────────────
    st.markdown("###  Resume Upload")
    st.markdown(
        "Upload your resume in PDF format. "
        "Our system will **automatically read and score** it using ML."
    )

    uploaded_file = st.file_uploader(
        label="Choose your resume (PDF only)",
        type=["pdf"],
        key="resume_upload",
        help="Max 5MB. Use a text-based PDF, not a scanned image."
    )

    parsed_resume = None

    if uploaded_file:
        st.success(
            f"**{uploaded_file.name}** uploaded "
            f"({uploaded_file.size / 1024:.1f} KB)"
        )

        with st.spinner(" Reading your resume..."):
            parsed_resume = parse_resume(uploaded_file)

        # Store in session state so re-runs don't re-parse
        st.session_state["parsed_resume"] = parsed_resume

        # ── RESUME DETECTION PREVIEW ──────────────────────────────────────────
        if parsed_resume["raw_text"]:
            st.markdown("#### Detected From Your Resume")

            with st.container(border=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Skills**")
                    if parsed_resume["skills_list"]:
                        pills = " ".join([
                            f"<span style='background:#e8f4fd;color:#1565c0;"
                            f"padding:2px 8px;border-radius:10px;"
                            f"font-size:12px;margin:2px;display:inline-block'>"
                            f"{s}</span>"
                            for s in parsed_resume["skills_list"][:10]
                        ])
                        extra = len(parsed_resume["skills_list"]) - 10
                        if extra > 0:
                            pills += (
                                f"<span style='color:#888;font-size:12px'>"
                                f" +{extra} more</span>"
                            )
                        st.markdown(pills, unsafe_allow_html=True)
                    else:
                        st.caption("No skills matched — raw text will be used")

                with col2:
                    st.markdown("**Profile**")
                    st.markdown(
                        f"<table style='font-size:13px;width:100%'>"
                        f"<tr><td style='color:#666;padding:2px 0'>Experience</td>"
                        f"<td><b>{parsed_resume['experience_years']} yrs</b></td></tr>"
                        f"<tr><td style='color:#666;padding:2px 0'>Education</td>"
                        f"<td><b>{parsed_resume['education']}</b></td></tr>"
                        f"<tr><td style='color:#666;padding:2px 0'>Certification</td>"
                        f"<td><b>{parsed_resume['certifications']}</b></td></tr>"
                        f"<tr><td style='color:#666;padding:2px 0'>Projects</td>"
                        f"<td><b>{parsed_resume['projects_count']}</b></td></tr>"
                        f"</table>",
                        unsafe_allow_html=True
                    )

                with col3:
                    st.markdown("**Role Match**")
                    role = parsed_resume["job_role"]
                    if role:
                        st.markdown(
                            f"<span style='background:#e8f5e9;color:#2e7d32;"
                            f"padding:4px 12px;border-radius:10px;"
                            f"font-size:13px;font-weight:600'>{role}</span>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.caption("Role not detected")

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(
                        f"<p style='font-size:13px;color:#555'>"
                        f"<b>{parsed_resume['skill_count']}</b> skills found</p>",
                        unsafe_allow_html=True
                    )

            st.info(
                "The ML model will use this detected information to score "
                "your application. Make sure your PDF is text-based for best results."
            )

        else:
            st.warning(
                "Could not extract text from this PDF. "
                "Please use a text-based PDF (not a scanned image). "
                "You can still submit — the employer will review manually."
            )

    elif "parsed_resume" in st.session_state:
        parsed_resume = st.session_state["parsed_resume"]

    st.divider()

    # SECTION 2: Screening Questions
    st.markdown("### Screening Questions")
    st.markdown("Please answer all questions honestly and in detail.")

    q1 = st.text_area(
        "1. Why are you interested in this position and what draws you to this company?",
        placeholder="Tell us what excites you about this role...",
        height=100, key="q1"
    )
    q2 = st.text_area(
        "2. Describe your most relevant experience for this role.",
        placeholder="Highlight specific skills, projects or accomplishments...",
        height=100, key="q2"
    )

    col1, col2 = st.columns(2)
    with col1:
        q3 = st.selectbox(
            "3. How many years of relevant experience do you have?",
            options=["Less than 1 year", "1 - 2 years", "3 - 5 years",
                     "5 - 10 years", "More than 10 years"],
            key="q3"
        )
    with col2:
        q4 = st.selectbox(
            "4. What is your availability to start?",
            options=["Immediately", "Within 2 weeks", "Within 1 month",
                     "Within 3 months", "Other"],
            key="q4"
        )

    st.divider()

    # SECTION 3: AI Interview Question Placeholder
    st.markdown("### AI-Generated Interview Question")
    with st.container(border=True):
        st.markdown(
            "<div style='background:#f0f4ff;padding:16px;border-radius:8px;"
            "border-left:4px solid #3b5bdb'>"
            "<p style='margin:0;color:#3b5bdb;font-weight:600'>AI Interview Question</p>"
            "<p style='margin:8px 0 0;color:#444'>This question will be dynamically "
            "generated by your AI model based on the job description.</p>"
            "<p style='margin:8px 0 0;color:#888;font-size:13px'>"
            "[ Wire your Claude / OpenAI API call here ]</p>"
            "</div>",
            unsafe_allow_html=True
        )
        ai_answer = st.text_area(
            "Your answer:", placeholder="Type your answer here...",
            height=100, key="ai_answer"
        )
    st.divider()

    # SECTION 4: Submit
    st.markdown("### Ready to Submit?")
    agreed = st.checkbox("I confirm that all information provided is accurate.")
    submit_clicked = st.button(
        "Submit Application",
        type="primary",
        use_container_width=True,
        disabled=not agreed
    )

    if submit_clicked:
        errors = []
        if not uploaded_file and not st.session_state.get("parsed_resume"):
            errors.append("Please upload your resume (PDF).")
        if not q1.strip():
            errors.append("Please answer question 1.")
        if not q2.strip():
            errors.append("Please answer Question 2.")

        if errors:
            for e in errors:
                st.error(e)
            return

        final_parsed = st.session_state.get("parsed_resume") or parsed_resume

        if uploaded_file:
            uploaded_file.seek(0)
            resume_path = save_resume(uploaded_file, seeker_id, job["id"])
        else:
            resume_path = ""

        answers = {
            "Why interested in this role?": q1.strip(),
            "Most relevant experience": q2.strip(),
            "Years of experience": q3,
            "Availability to start": q4,
            "AI interview question response": ai_answer.strip() or "Not answered",
        }
        answers_json = json.dumps(answers)

        saved = create_application(
            job_id=job["id"],
            seeker_id=seeker_id,
            resume_path=resume_path,
            answers_json=answers_json
        )

        if not saved:
            st.error("You have already applied to this job.")
            return

        # Score with Real ML
        with st.spinner("Scoring Your Resume..."):
            if final_parsed:
                score, label = score_resume(final_parsed, job=job)
            else:
                score, label = .0, "No resume data"

        from db import get_applications_by_seeker
        all_apps = get_applications_by_seeker(seeker_id)
        latest_app = all_apps[0] if all_apps else None
        if latest_app:
            update_application_score(latest_app["id"], score, label)

        st.session_state["last_score"] = score
        st.session_state["last_label"] = label
        st.session_state.pop("parsed_resume", None)
        st.session_state["apply_stage"] = "success"
        st.rerun()


# STAGE 3 SUCCESS SCREEN
def show_success_screen(job):
    st.balloons()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.markdown(
            "<div style='text-align:center;padding:2rem 0'>"
            "<div style='font-size:64px'></div>"
            "<h2>Application Submitted!</h2>"
            "</div>",
            unsafe_allow_html=True
        )

        with st.container(border=True):
            st.markdown(f"**Position:** {job['title']}")
            st.markdown(f"**Company:** {job['company']}")
            st.markdown(f"**Location:** {job['location']}")

            score = st.session_state.get("last_score")
            label = st.session_state.get("last_label")

            if score is not None:
                st.divider()
                colour = (
                    "#2e7d32" if score >= 65 else
                    "#e65100" if score >= 40 else
                    "#c62828"
                )
                st.markdown("**Your ML Match Score:**")
                st.markdown(
                    f"<div style='background:#e0e0e0;border-radius:8px;"
                    f"height:16px;width:100%'>"
                    f"<div style='background:{colour};width:{score}%;"
                    f"height:16px;border-radius:8px'></div></div>"
                    f"<p style='color:{colour};font-weight:700;"
                    f"font-size:18px;margin-top:6px'>"
                    f"{score:.0f}/100 — {label}</p>",
                    unsafe_allow_html=True
                )
                matched = st.session_state.get("matched_skills", [])
                missing = st.session_state.get("missing_skills", [])
                job_skills = st.session_state.get("job_skills", [])

                if job_skills:
                    st.divider()
                    st.markdown("**Skills Match Breakdown:**")
                    col_m, col_x = st.columns(2)

                    with col_m:
                        st.markdown("**You have:**")
                        if matched:
                            for s in matched:
                                st.markdown(
                                    f"<span style='background:#e8f5e9;color:#2e7d32;"
                                    f"padding:2px 8px;border-radius:8px;font-size:12px;"
                                    f"margin:2px;display:inline-block'>✓ {s}</span>",
                                    unsafe_allow_html=True
                                )
                        else:
                            st.caption("None matched")

                    with col_x:
                        st.markdown("**Job also wants:**")
                        if missing:
                            for s in missing[:0]: # cap at 8 so it doesn't overflow
                                st.markdown(
                                    f"<span style='background:#fdecea;color:#c62828;"
                                    f"padding:2px 8px;border-radius:8px;font-size:12px;"
                                    f"margin:2px;display:inline-block'>✗ {s}</span>",
                                    unsafe_allow_html=True
                                )
                        else:
                            st.caption("You covered all required skills!")

    st.markdown("---")
    st.markdown("### What happens next?")
    st.markdown(
        "1. Your resume has been **scored by our ML model**.\n"
        "2. The employer will review your application and score.\n"
        "3. You will receive an **email notification** once a decision is made.\n"
        "4. Track your application status in **My Applications**."
    )
    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("View My Applications", use_container_width=True, type="primary"):
            for key in ["selected_job_id", "apply_stage", "last_score", "last_label"]:
                st.session_state.pop(key, None)
            st.session_state["current_page"] = "seeker_dashboard"
            st.rerun()
    with col_b:
        if st.button("Browse More Jobs", use_container_width=True):
            for key in ["selected_job_id", "apply_stage", "last_score", "last_label",
                        "matched_skills", "missing_skills", "job_skills"]:
                st.session_state.pop(key, None)
            st.session_state["current_page"] = "seeker_dashboard"
            st.rerun()


# MAIN FUNCTION called from app.py
def show_apply_page():
    seeker_id = st.session_state["user_id"]

    job_id = st.session_state.get("selected_job_id")
    if not job_id:
        st.warning("No job selected. Please choose a job from the job board.")
        if st.button("Back to Jobs"):
            st.session_state["current_page"] = "seeker_dashboard"
            st.rerun()
        return

    job = get_job_by_id(job_id)
    if not job:
        st.error("Job not found. It may have been removed.")
        if st.button("Back to Jobs"):
            st.session_state["current_page"] = "seeker_dashboard"
            st.rerun()
        return

    if "apply_stage" not in st.session_state:
        st.session_state["apply_stage"] = "detail"

    stage = st.session_state["apply_stage"]

    if stage == "detail":
        show_job_details(job, seeker_id)
    elif stage == "form":
        show_application_form(job, seeker_id)
    elif stage == "success":
        show_success_screen(job)
