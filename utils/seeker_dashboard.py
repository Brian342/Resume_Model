"""
seeker_dashboard.py — Job Seeker Section
=========================================
This file contains ONE function: show_seeker_dashboard()
It is imported and called from app.py inside the main() router.

It has three tabs:
  Tab 1 — Overview        : dynamic stat metrics + a pie chart of application statuses
  Tab 2 — My Applications : list of every job the seeker has applied to with status + score
  Tab 3 — Browse Jobs     : job cards grid — clicking "View & Apply" stores the job in
                            session_state and routes to the apply page

IMPORTS USED:
  db.py — get_seeker_stats, get_applications_by_seeker, get_all_active_jobs, has_applied
  streamlit — all UI components
  plotly — pie chart on the overview tab

INSTALL:
  pip install plotly
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from db import (
    get_seeker_stats,
    get_applications_by_seeker,
    get_seeker_preferences,
    save_seeker_preferences,
    get_all_active_jobs,
    has_applied
)


# Helper Status Badge
def status_badge(status: str) -> str:
    """
    Returns a coloured HTML pill badge for an application status.
    we use st.markdown(..., unsafe_allow_html=True) to render these.

    Pending -> grey pill
    approved -> green pill
    rejected -> red pill
    """
    colours = {
        "pending": ("#f0f0f0", "#555555"),
        "approved": ("#e6f4ea", "#2e7d32"),
        "rejected": ("#fdecea", "#c62828"),
    }
    bg, fg = colours.get(status, ("#f0f0f0", "#555555"))
    label = status.upper()
    return (
        f"<span style='background:{bg};color:{fg};padding:3px 10px;"
        f"border-radius:12px;font-size:12px;font-weight:600'>{label}</span>"
    )


# Helper Score Bar
def score_bar(score) -> str:
    """
    Returns an HTML progress Bar coloured by score Value.
    Returns a 'Not scored Yet' message if score is None.

    This is the same visual used in the employer dashboard,
    so both sides see a consistent score representation.
    """
    if score is None:
        return "<span style='color:#888;font-size:13px'>Not scored Yet</span>"

    if score >= 70:
        colour = "#2e7d32"  # green
    elif score >= 40:
        colour = "#e65100"  # orange
    else:
        colour = "#c62828"  # red

    return (
        f"<div style='background:#e0e0e0;border-radius:8px;height:12px;width:100%'>"
        f"<div style='background:{colour};width:{score}%;height:12px;border-radius:8px'>"
        f"</div></div>"
        f"<span style='color:{colour};font-size:12px;font-weight:600'>"
        f"{score:.0f}/100</span>"
    )


# Tab 1 Overview
def show_overview_tab(seeker_id: int):
    """
    Displays four dynamic metric cards and a pie chart
    showing the breakdown of the seeker's application statuses.

    seeker_id: logged-in user's ID from session_state
    """
    # get_seeker_stats returns a dict:
    # {"total_applied": 5, "qualified": 2, "pending": 2, "rejected": 1}
    stats = get_seeker_stats(seeker_id)

    # metric cards
    # Four equal columns, one metric each
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        label="Total Applied",
        value=stats["total_applied"],
        help="Total number of Jobs you have applied to"
    )
    c2.metric(
        label="Qualified",
        value=stats["qualified"],
        delta=f"{stats['qualified']} approved",  # delta shows a small +/- indicator
        delta_color="normal",
        help="Applications where the employer approved you"
    )
    c3.metric(
        label="Pending",
        value=stats["pending"],
        help="Applications still awaiting employer review"
    )
    c4.metric(
        label="Rejected",
        value=stats["rejected"],
        delta=stats["rejected"] if stats["rejected"] > 0 else None,
        delta_color="inverse",  # Inverse make the delta red when negative
        help="Applications that were not successful"
    )

    st.divider()

    # pie chart
    # only shows the chart if the seeker has at least one application
    if stats["total_applied"] == 0:
        st.info("You haven't applied to any jobs yet. Head to the **Browse Jobs** tab to get started!")
        return

    st.markdown("### Application Status Breakdown")

    # Build the data for the chart
    # we filter out categories with 0 so the chart doesn't show empty slices
    labels = []
    values = []
    colors = []

    status_map = [
        ("Approved", stats["qualified"], "#2e7d32"),
        ("Pending", stats["pending"], "#f9a825"),
        ("Rejected", stats["rejected"], "#c62828"),
    ]
    for label, value, color in status_map:
        if value > 0:
            labels.append(label)
            values.append(value)
            colors.append(color)

    # Plotly express make charts very easy - one line creates the figure
    fig = px.pie(
        names=labels,
        values=values,
        color_discrete_sequence=colors,
        hole=.45,  # Makes it a donut chart
    )

    # Customize the chart apperance
    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>"
    )
    fig.update_layout(
        showlegend=True,
        height=360,
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",  # transparent background
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=.5)
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### Summary")
        st.markdown(f"You have applied to **{stats['total_applied']}** job(s) in total.")
        if stats["qualified"] > 0:
            st.success(f"Congratulations! you have been approved for **{stats['qualified']}** Position(s).")
        if stats["pending"] > 0:
            st.info(f"**{stats['pending']}** application(s) are still under review.")
        if stats["rejected"] > 0:
            st.warning(
                f"Keep going! **{stats['rejected']}** application(s) were unsuccessful - more opportunities await.")


# Tab 2 My Applications
def show_my_applications_tab(seeker_id: int):
    """
    Shows a detailed list of every job the seeker has applied to.
    Each row shows: job title, company, date applied, Ai Score Bar, status badge.

    Seeker_id: logged-in user's ID from session_state
    """
    st.markdown("### My Applications")

    # get_applications_by_seeker joins the jobs table so each row
    # has job_title, company, location fields alongside the application data
    applications = get_applications_by_seeker(seeker_id)

    if not applications:
        st.info("No Applications yet. Got to **Browse Jobs** to apply!")
        return

    # Filter bar
    # let the seeker filter by status - useful once they have many applications
    filter_status = st.selectbox(
        "Filter by Status",
        options=["All", "Pending", "Approved", "Rejected"],
        index=0,
        key="app_filter"
    )

    # apply the filter
    if filter_status != "All":
        applications = [a for a in applications if a["status"] == filter_status.lower()]

    if not applications:
        st.info(f"No {filter_status.lower()} applications found.")
        return

    st.markdown(f"Showing **{len(applications)}** application(s)")
    st.divider()

    # Application Cards
    for app in applications:
        # Each application is shown in a container (a subtle bordered box)
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"### {app['job_title']}")
                st.markdown(f"**{app['company']}**  {app['location']}")
                st.markdown(
                    f"Applied on: `{str(app['applied_at'])[:10]}`"
                )

            with col2:
                st.markdown("**AI Match Score**")
                # Render the HTML Progress Bar
                st.markdown(score_bar(app["ai_score"]), unsafe_allow_html=True)

                if app["ml_label"]:
                    st.markdown(
                        f"<span style='font-size:13px;color:#555'>ML: {app['ml_label']}</span>",
                        unsafe_allow_html=True

                    )
            with col3:
                st.markdown("**Status**")
                # Render the coloured status pill
                st.markdown(status_badge(app["status"]), unsafe_allow_html=True)


# Tab 3 Browse Jobs
def show_browse_jobs_tab(seeker_id: int):
    """
    Displays all active job listings as cards in a 2-column grid

    Each card shows:
        - Job Title + company name
        - Location and Salary
        - A short preview of the description
        - A "View and Apply" button Or "Already Applied" if they've applied

    Clicking "View and Apply" stores the Job ID in Session_state
    and routes to the apply page

    seeker_id: Used to check which jobs the seeker has already applied to
    """
    st.markdown("### Available Jobs")

    jobs = get_all_active_jobs()

    if not jobs:
        st.info("No job listings available right now. check back soon!")
        return

    # Load seeker preferences
    prefs = get_seeker_preferences(seeker_id)
    categories = [c.lower() for c in prefs["categories"]]
    keywords = [k.lower() for k in prefs["keywords"]]

    # Filter jobs by preference
    # A job matches if its title OR description contains any preferred
    # category word or keyword. We do a soft match so "Technology & Software"
    # matches jobs with "software", "developer", "engineer" in the title

    CATEGORY_KEYWORDS = {
        "technology & software": [
            "software engineer", "software developer", "web developer",
            "mobile developer", "backend developer", "frontend developer",
            "full stack", "fullstack", "programmer", "application developer",
        ],
        "data science & ai": [
            "data scientist", "machine learning engineer", "ml engineer",
            "data analyst", "data engineer", "nlp engineer", "deep learning",
            "ai engineer", "business intelligence", "bi analyst",
            "analytics engineer", "data science",
        ],
        "cybersecurity": [
            "cybersecurity", "cyber security", "penetration tester",
            "ethical hacker", "security analyst", "soc analyst",
            "information security", "siem", "vulnerability",
        ],
        "networking & infrastructure": [
            "network engineer", "network administrator", "network admin",
            "infrastructure engineer", "devops engineer", "cloud engineer",
            "systems administrator", "sysadmin", "cisco", "network architect",
        ],
        "human resources": [
            "human resource", "hr manager", "hr officer", "hr business partner",
            "hrbp", "recruitment", "talent acquisition", "talent manager",
            "payroll", "people operations", "people ops",
        ],
        "finance & accounting": [
            "financial analyst", "finance manager", "accountant", "accounting",
            "auditor", "audit manager", "tax consultant", "budget analyst",
            "treasurer", "cfo", "financial controller", "accounts payable",
            "accounts receivable",
        ],
        "marketing & sales": [
            "marketing manager", "digital marketing", "brand manager",
            "seo specialist", "content marketer", "sales manager",
            "crm manager", "growth marketer", "social media manager",
        ],
        "operations & management": [
            "operations manager", "project manager", "supply chain manager",
            "logistics manager", "procurement manager", "operations analyst",
            "business analyst", "program manager",
        ],
        "design & creative": [
            "ui designer", "ux designer", "graphic designer", "creative director",
            "visual designer", "product designer", "motion designer",
            "figma", "illustrator", "web designer",
        ],
        "healthcare": [
            "nurse", "doctor", "physician", "clinical officer", "pharmacist",
            "medical officer", "health officer", "radiologist", "dentist",
        ],
        "legal": [
            "lawyer", "attorney", "legal counsel", "legal officer",
            "compliance officer", "paralegal", "advocate",
        ],
        "other": [],
    }

    def job_matches_preferences(job) -> bool:
        """
        Returns True if the job matches any of the seeker's saved preferences.

        Matching strategy (ordered by precision):
          1. Check job TITLE against the category keyword list — most reliable.
          2. Check the seeker's custom keywords against the full job text.
          3. If the seeker selected 'Other', show all jobs that didn't match
             any specific category.
        """
        if not categories:
            return True   # no preferences saved — show every job

        job_title = job["title"].lower()
        job_full  = (
            job["title"] + " " + job["description"] + " " + job["requirements"]
        ).lower()

        for cat in categories:
            if cat == "other":
                return True   # 'Other' always shows all jobs

            cat_words = CATEGORY_KEYWORDS.get(cat, [])

            # ── Title-first check (exact phrase) ──────────────────────────────
            # Match on the title only first — this avoids Finance jobs appearing
            # for Data Science seekers just because "data" appears in the
            # job description somewhere.
            if any(phrase in job_title for phrase in cat_words):
                return True

            # ── Full-text fallback (multi-word phrases only) ──────────────────
            # Only use multi-word phrases (2+ words) for full-text search so we
            # don't get false positives from single common words.
            multi_word = [p for p in cat_words if " " in p]
            if any(phrase in job_full for phrase in multi_word):
                return True

        # ── Custom keyword check ──────────────────────────────────────────────
        for kw in keywords:
            if len(kw) > 3 and kw in job_full:   # skip very short keywords
                return True

        return False

    # Apply filter
    filtered_jobs = [j for j in jobs if job_matches_preferences(j)]

    # Preference badge
    if categories:
        pref_text = " · ".join(prefs["categories"])
        st.markdown(
            f"<div style='background:#e8f4fd;border-radius:8px;padding:10px 16px;"
            f"margin-bottom:12px;font-size:13px;color:#1565c0'>"
            f"<b>Showing jobs matching:</b> {pref_text} &nbsp;"
            f"<span style='color:#888'>({len(filtered_jobs)} of "
            f"{len(jobs)} jobs)</span></div>",
            unsafe_allow_html=True
        )
        # Let seeker toggle to see all jobs anyway
        show_all = st.toggle("Show all jobs (ignore preferences)", value=False)
        if show_all:
            filtered_jobs = jobs

    # search bar
    # simple client-side filter - no extra DB call needed
    search = st.text_input(
        "Search Jobs",
        placeholder="Search by Title, Company or Location...",
        key="job_search"
    ).lower()

    # Filter jobs based on the search term
    display_jobs = filtered_jobs if categories else jobs
    if search:
        display_jobs = [
            j for j in display_jobs
            if search in j["title"].lower()
               or search in j["company"].lower()
               or search in j["location"].lower()
        ]

    if not display_jobs:
        st.info("No Jobs Match your Search. Try different keywords. "
                "Toggle 'Show all jobs' above or update your preferences from the sidebar.")
        return

    st.markdown(f"**{len(display_jobs)}** job(s) found")
    st.divider()

    # 2-column card grid — uses display_jobs (already filtered + searched)
    from itertools import zip_longest
    pairs = list(zip_longest(display_jobs[0::2], display_jobs[1::2]))

    for left_job, right_job in pairs:
        col1, col2 = st.columns(2)

        for col, job in zip([col1, col2], [left_job, right_job]):
            if job is None:
                continue  # Last row with odd number of Jobs - leave right col empty

            with col:
                with st.container(border=True):
                    # job title and company
                    st.markdown(f"#### {job['title']}")
                    st.markdown(f"**{job['company']}**")

                    # location and salary row
                    loc_sal_col1, loc_sal_col2 = st.columns(2)
                    with loc_sal_col1:
                        st.markdown(f"{job['location']}")
                    with loc_sal_col2:
                        st.markdown(f"{job['salary'] or 'Not specified'}")

                    # Short description preview - first 120 characters
                    preview = job["description"][:120]
                    if len(job["description"]) > 120:
                        preview += "..."
                    st.markdown(
                        f"<p style='color:#666;font-size:14px:margin:8px 0'>{preview}</p>",
                        unsafe_allow_html=True
                    )

                    st.markdown("---")

                    # check if already applied - show different button
                    already_applied = has_applied(job["id"], seeker_id)

                    if already_applied:
                        st.markdown(
                            "<span style='color:#2e7d32;font-weight:600;"
                            "font-size:14px'> Already Applied</span>",
                            unsafe_allow_html=True
                        )
                    else:
                        # "View & Apply" stores the selected job in session_state
                        # and navigates to the apply page
                        # key must be unique per job - we use the job ID
                        if st.button(
                                "View & Apply",
                                key=f"apply_btn_{job['id']}",
                                use_container_width=True,
                                type="primary"
                        ):
                            # store which job they selected
                            st.session_state["selected_job_id"] = job["id"]
                            st.session_state["apply_stage"] = "detail"
                            st.session_state["current_page"] = "apply"
                            st.rerun()


# Tab 4 — Job Preferences
def show_preferences_tab(seeker_id: int):
    """
    Lets the seeker update their job category preferences at any time
    from inside the dashboard — no need to log out and log back in.
    """
    ALL_CATEGORIES = [
        "Technology & Software",
        "Data Science & AI",
        "Cybersecurity",
        "Networking & Infrastructure",
        "Human Resources",
        "Finance & Accounting",
        "Marketing & Sales",
        "Operations & Management",
        "Design & Creative",
        "Healthcare",
        "Legal",
        "Other",
    ]

    st.markdown("### My Job Preferences")
    st.markdown(
        "Update the job categories you are interested in. "
        "Your job board will immediately reflect these changes."
    )
    st.divider()

    # Load existing preferences so the selectors are pre-filled
    prefs = get_seeker_preferences(seeker_id)
    current_cats = prefs["categories"]
    current_kws  = prefs["keywords"]

    selected_cats = st.multiselect(
        "Job Categories (select all that apply)",
        options=ALL_CATEGORIES,
        default=current_cats if current_cats else [],
        key="dash_pref_categories",
    )

    keywords_str = st.text_input(
        "Specific skills or keywords (optional)",
        value=", ".join(current_kws) if current_kws else "",
        placeholder="e.g. python, machine learning, remote",
        key="dash_pref_keywords",
        help="Comma-separated. Jobs containing these words will be prioritised.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Preferences", type="primary",
                     use_container_width=True, key="save_prefs_dash"):
            if not selected_cats:
                st.warning("Please select at least one category.")
            else:
                kw_list = [k.strip() for k in keywords_str.split(",") if k.strip()]
                save_seeker_preferences(
                    seeker_id=seeker_id,
                    categories=", ".join(selected_cats),
                    keywords=", ".join(kw_list),
                )
                st.success(
                    "Preferences saved! Head to **Browse Jobs** to see your updated listings."
                )
                # Clear any cached state so the job board re-filters immediately
                st.session_state.pop("show_preferences", None)

    with col2:
        if st.button("Reset to All Jobs", use_container_width=True,
                     key="reset_prefs_dash"):
            save_seeker_preferences(
                seeker_id=seeker_id,
                categories="",
                keywords="",
            )
            st.info("Preferences cleared — you will now see all available jobs.")

    # Show a live preview of current saved preferences
    if current_cats:
        st.divider()
        st.markdown("**Currently saved preferences:**")
        pills = " &nbsp; ".join([
            f"<span style='background:#e8f4fd;color:#1565c0;padding:3px 10px;"
            f"border-radius:12px;font-size:13px;font-weight:500'>{c}</span>"
            for c in current_cats
        ])
        st.markdown(pills, unsafe_allow_html=True)
        if current_kws:
            st.caption(f"Keywords: {', '.join(current_kws)}")


# Main Function
def show_seeker_dashboard():
    """
    Entry point for this page.
    app.py calls this when current_page == "seeker_dashboard".

    Read seeker ID from session_state and render four tabs.
    """
    seeker_id = st.session_state["user_id"]

    st.title("My Dashboard")
    st.markdown(f"Welcome, **{st.session_state['user_name']}**")
    st.divider()

    tabs1, tabs2, tabs3, tabs4 = st.tabs([
        "Overview", "My Applications", "Browse Jobs", "Job Preferences"
    ])

    with tabs1:
        show_overview_tab(seeker_id)

    with tabs2:
        show_my_applications_tab(seeker_id)

    with tabs3:
        show_browse_jobs_tab(seeker_id)

    with tabs4:
        show_preferences_tab(seeker_id)