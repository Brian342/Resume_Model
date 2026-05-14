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
    st.markdown(
        "Answer **5 questions** tailored to this specific role. "
        "Your responses will be reviewed by the employer alongside your resume."
    )
    # QUESTION BANK keyed by job category
    QUESTION_BANK = {
        "software": [
            "Describe a challenging bug you encountered and how you debugged and resolved it.",
            "Explain the difference between object-oriented and functional programming with examples from your "
            "experience.",
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
            "How do you handle missing data in a dataset? Walk through your decision process.",
            "Explain the difference between supervised and unsupervised learning with a real-world example.",
            "Describe a machine learning model you deployed. What challenges did you face in production?",
            "How do you evaluate whether a model is overfitting or underfitting, and what do you do about it?",
            "Walk us through how you would approach a new classification problem from scratch.",
            "What metrics would you use to evaluate a recommendation system, and why?",
            "Describe a time you communicated complex data findings to a non-technical stakeholder.",
            "How do you ensure data integrity and reproducibility in your analyses?",
            "What is your experience with cloud data platforms such as BigQuery, Redshift, or Databricks?",
        ],
        "cybersecurity": [
            "Describe the steps you would take when responding to a suspected data breach.",
            "What is the difference between a vulnerability assessment and a penetration test?",
            "How would you explain the concept of zero-trust architecture to a non-technical manager?",
            "Describe a time you identified a security vulnerability and how you handled it responsibly.",
            "What tools and techniques do you use for network monitoring and intrusion detection?",
            "Explain the OWASP Top 10 and give an example of how you have mitigated one of those risks.",
            "How do you stay updated on emerging threats and CVEs?",
            "What is your approach to security hardening a new server or cloud environment?",
            "Describe your experience with security information and event management (SIEM) platforms.",
            "How do you balance security requirements with usability and developer productivity?",
        ],
        "networking": [
            "Explain the OSI model and describe a real networking problem you solved using it.",
            "How would you troubleshoot a situation where users in one office subnet cannot reach a shared drive?",
            "Describe your experience designing or maintaining a network for high availability.",
            "What is your approach to capacity planning for network infrastructure?",
            "How have you used automation or infrastructure-as-code in your networking work?",
            "Describe a major network outage you were involved in resolving. What was the root cause?",
            "What is your experience with cloud networking (VPCs, VPNs, AWS/Azure/GCP networking)?",
            "Explain the difference between BGP and OSPF routing protocols and when you would use each.",
            "How do you approach network security — segmentation, firewall rules, and access control?",
            "What monitoring tools do you rely on for network health and performance?",
        ],
        "hr": [
            "Describe your end-to-end recruitment process for a hard-to-fill technical role.",
            "How do you handle a situation where a line manager and HR policy are in conflict?",
            "What strategies have you used to improve employee retention and reduce turnover?",
            "Describe how you have built or improved an onboarding programme.",
            "How do you ensure fairness and reduce bias during the interview and selection process?",
            "Describe a difficult performance management case you handled and how you resolved it.",
            "What is your experience with HR information systems (HRIS) and payroll platforms?",
            "How do you keep up with changes in labour law and ensure compliance?",
            "Describe how you have supported diversity, equity, and inclusion initiatives.",
            "How do you measure the effectiveness of an HR programme or initiative?",
        ],
        "finance": [
            "Walk us through how you would build a three-statement financial model from scratch.",
            "Describe a time you identified a significant financial discrepancy and how you resolved it.",
            "How do you approach variance analysis between actual and budgeted figures?",
            "What is your experience with financial forecasting and scenario planning?",
            "Describe your audit experience — internal, external, or both.",
            "How do you ensure accuracy and data integrity when working with large financial datasets?",
            "Explain the difference between cash-basis and accrual accounting and when each is appropriate.",
            "What accounting standards are you most familiar with (IFRS, GAAP, local GAAP)?",
            "How have you contributed to cost-reduction or efficiency improvement initiatives?",
            "Describe a time you presented complex financial information to senior leadership.",
        ],
        "marketing": [
            "Describe a marketing campaign you led from strategy to execution. What were the results?",
            "How do you define and segment your target audience for a new product launch?",
            "What metrics do you track to evaluate the success of a digital marketing campaign?",
            "Describe your experience with SEO — both on-page and off-page strategies.",
            "How do you build and maintain a brand voice consistently across different channels?",
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

    def _detect_job_category(job) -> str:
        """Map the job title/description to a question bank key."""
        title = job["title"].lower()
        full_text = (job["title"] + " " + job["description"] + " " + job["requirements"]).lower()

        if any(w in title for w in [
            "hr", "human resource", "human resources", "recruitment",
            "talent acquisition", "talent management", "payroll",
            "people operations", "people ops", "hrbp",
        ]):
            return "hr"
        if any(w in title for w in [
            "finance", "financial", "accounting", "accountant",
            "audit", "auditor", "tax", "budget", "treasurer", "cfo",
        ]):
            return "finance"

        if any(w in title for w in [
            "marketing", "brand", "seo", "digital marketing",
            "content", "campaign", "crm", "growth",
        ]):
            return "marketing"

        if any(w in title for w in [
            "security", "cyber", "penetration", "soc", "siem", "ethical hack",
        ]):
            return "cybersecurity"

        if any(w in title for w in [
            "network", "networking", "infrastructure", "cisco",
            "devops", "cloud engineer", "systems admin", "sysadmin", "network admin",
        ]):
            return "networking"

        if any(w in title for w in [
            "data scientist", "machine learning", "data analyst",
            "nlp", "deep learning", "data engineer", "bi analyst", "analytics",
        ]):
            return "data"

        if any(w in title for w in [
            "software", "developer", "programmer", "web developer",
            "mobile", "backend", "frontend", "full stack", "fullstack",
        ]):
            return "software"

        if any(w in title for w in [
            "operations", "project manager", "supply chain",
            "logistics", "procurement", "operations manager",
        ]):
            return "operations"

        if any(w in title for w in [
            "design", "designer", "ui", "ux", "graphic", "figma",
            "creative", "illustrator",
        ]):
            return "design"

            # noinspection PyUnreachableCode
            if any(w in full_text for w in [
                "human resource", "hr manager", "hr officer", "recruitment",
                "talent acquisition", "payroll", "people operations",
            ]):
                return "hr"
            if any(w in full_text for w in [
                "finance", "accounting", "audit", "financial analyst",
                "tax", "budget", "treasurer",
            ]):
                return "finance"
            if any(w in full_text for w in [
                "marketing", "brand", "seo", "digital marketing",
                "content strategy", "campaign", "crm",
            ]):
                return "marketing"
            if any(w in full_text for w in [
                "security", "cyber", "penetration", "soc ", "siem", "ethical hack",
            ]):
                return "cybersecurity"
            if any(w in full_text for w in [
                "network admin", "network engineer", "infrastructure",
                "cisco", "devops", "cloud engineer", "systems admin", "sysadmin",
            ]):
                return "networking"
            if any(w in full_text for w in [
                "data scientist", "machine learning", "data analyst",
                "nlp", "deep learning", "data engineer", "bi ", "analytics",
            ]):
                return "data"
            if any(w in full_text for w in [
                "software engineer", "software developer", "backend developer",
                "frontend developer", "full stack", "mobile developer",
            ]):
                return "software"
            if any(w in full_text for w in [
                "operations manager", "project manager", "supply chain",
                "logistics", "procurement",
            ]):
                return "operations"
            if any(w in full_text for w in [
                "ux designer", "ui designer", "graphic designer", "figma",
                "creative director",
            ]):
                return "design"

            return "general"

    # Seed questions from the detected category: pad with general if needed
    import random
    category_key = _detect_job_category(job)
    category_pool = QUESTION_BANK.get(category_key, [])
    general_pool = QUESTION_BANK["general"]

    # Combine and deduplicate, then pick 5
    combined = list(dict.fromkeys(category_pool + general_pool))  # Preserve order, no dups

    # Use job_id as seed so the same job always shows the same 5 questions
    rng = random.Random(job["id"])
    selected_questions = rng.sample(combined, min(5, len(combined)))

    # Persist questions in session_state so re-runs don't reshuffle mid-form
    q_key = f"interview_qs_{job['id']}"
    if q_key not in st.session_state:
        st.session_state[q_key] = selected_questions
    interview_questions = st.session_state[q_key]

    # Render a text area for each question and collect answers

    st.markdown(
        f"<div style='background:#f0f4ff;border-left:4px solid #3b5bdb;"
        f"padding:10px 16px;border-radius:8px;margin-bottom:12px;font-size:13px;color:#1565c0'>"
        f"<b>Role detected:</b> {category_key.replace('_', ' ').title()} &nbsp;·&nbsp; "
        f"Answer all 5 questions as fully as you can.</div>",
        unsafe_allow_html=True
    )
    ai_answer = {}
    for i, question in enumerate(interview_questions, start=1):
        answer = st.text_area(
            f"Q{i}. {question}",
            placeholder="Type your answer here...",
            height=100,
            key=f"iq_{job['id']}_{i}"
        )
        ai_answer[f"Interview Q{i}: {question}"] = answer.strip() or "Not answered"

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
            **ai_answer,
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
        # Clear interview questions cache for this job
        st.session_state.pop(f"interview_qs_{job['id']}", None)
        st.session_state["apply_stage"] = "success"
        st.rerun()


# STAGE 3 SUCCESS SCREEN
def show_success_screen(job):
    st.balloons()

    # Larger, more impactful header
    st.markdown("<h1 style='text-align:center; padding-bottom: 20px;'>Application Submitted!</h1>",
                unsafe_allow_html=True)

    with st.container(border=True):
        # Top Row: Info and Skills
        col_info, col_skills = st.columns([1, 1], gap="large")

        with col_info:
            st.markdown(f"### {job['title']}")
            st.markdown(f"**{job['company']}** | {job['location']}")

            score = st.session_state.get("last_score")
            label = st.session_state.get("last_label")

            if score is not None:
                st.write("")
                colour = "#2e7d32" if score >= 65 else "#e65100" if score >= 40 else "#c62828"
                st.markdown(f"#### Match Score: <span style='color:{colour}'>{score:.0f}/100</span>",
                            unsafe_allow_html=True)
                st.markdown(
                    f"<div style='background:#f0f2f6; border-radius:15px; height:20px; width:100%; margin-top:10px;'>"
                    f"<div style='background:{colour}; width:{score}%; height:20px; border-radius:15px;'></div></div>",
                    unsafe_allow_html=True
                )
                st.info(f"**Status:** {label}")

        with col_skills:
            st.markdown("### Skills Analysis")
            matched = st.session_state.get("matched_skills", [])
            missing = st.session_state.get("missing_skills", [])

            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.markdown("**Matches**")
                if matched:
                    for s in matched[:6]:
                        st.markdown(f"<p style='font-size:16px; margin:0; color:#2e7d32;'>✓ {s}</p>",
                                    unsafe_allow_html=True)
                else:
                    st.caption("No direct matches")

            with s_col2:
                st.markdown("**Missing**")
                if missing:
                    for s in missing[:6]:
                        # Increased font size for readability
                        st.markdown(
                            f"<span style='background:#fdecea;color:#c62828;padding:2px "
                            f"8px;border-radius:8px;font-size:12px;margin:2px;display:inline-block'>𝑥 {s}</span>",
                            unsafe_allow_html=True)
                else:
                    st.caption("Perfect coverage!")

        st.divider()

        # Bottom Row: Next Steps & Navigation
        col_text, col_btns = st.columns([1.5, 1], gap="medium")

        with col_text:
            st.markdown("#### What happens next?")
            st.write(
                "1. Your resume has been **scored by our ML model**.\n"
                "2. The employer will review your application and score.\n"
                "3. You will receive an **email notification** once a decision is made.\n"
                "4. Track your application status in **My Applications**."
            )

        with col_btns:
            st.write("")  # Alignment spacer
            if st.button("View My Applications", use_container_width=True, type="primary"):
                for key in ["selected_job_id", "apply_stage", "last_score", "last_label"]:
                    st.session_state.pop(key, None)
                st.session_state["current_page"] = "seeker_dashboard"
                st.rerun()

            if st.button("Browse More Jobs", use_container_width=True):
                for key in ["selected_job_id", "apply_stage", "last_score", "last_label", "matched_skills",
                            "missing_skills", "job_skills"]:
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
