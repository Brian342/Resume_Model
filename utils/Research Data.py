"""
research_data.py
================
Interview questions, questionnaire questions, and simulated
response data for Chapter 3 of the Job Matching System report.

Run this file to generate all charts:
    python research_data.py

Charts produced:
    1.  interview_seeker_q1.png   — How long does job search take?
    2.  interview_seeker_q2.png   — Main challenge in applying
    3.  interview_employer_q1.png — How long to screen resumes?
    4.  interview_employer_q2.png — % of applications qualified
    5.  quest_seeker_bar.png      — Seeker questionnaire bar chart
    6.  quest_employer_bar.png    — Employer questionnaire bar chart
    7.  quest_seeker_likert.png   — Seeker Likert scale heatmap
    8.  quest_employer_likert.png — Employer Likert scale heatmap
    9.  combined_summary.png      — Side-by-side overview

Install requirements:
    pip install matplotlib pandas numpy seaborn
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ──────────────────────────────────────────────────────────────────
#  COLOUR PALETTE  (matches Pioneer Insurance blue theme)
# ──────────────────────────────────────────────────────────────────
BLUE   = "#1E2761"
LBLUE  = "#4A90D9"
GREEN  = "#2e7d32"
LGREEN = "#81c784"
RED    = "#c62828"
AMBER  = "#f9a825"
GREY   = "#9e9e9e"
BG     = "#F4F7FE"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor":   BG,
    "font.family":      "DejaVu Sans",
    "axes.spines.top":  False,
    "axes.spines.right":False,
})


# ══════════════════════════════════════════════════════════════════
#
#   PART A — INTERVIEW QUESTIONS & RESPONSES
#   (Semi-structured qualitative + quantitative questions)
#   Sample size: 10 participants per group
#
# ══════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────
#  INTERVIEW: JOB SEEKERS  (10 participants)
# ─────────────────────────────────────────────
"""
INTERVIEW GUIDE — JOB SEEKERS
Conducted with: University students + recent graduates
Format: Online, semi-structured, 20–30 minutes

OPEN-ENDED QUESTIONS (qualitative — summarised in report prose):
  IQ-S1. Walk me through your typical process when applying for a job.
  IQ-S2. What is the most frustrating part of the job application process?
  IQ-S3. Have you ever received feedback after submitting a resume? 
          If yes, how was it communicated?
  IQ-S4. How do you currently decide which jobs to apply to?
  IQ-S5. If a system automatically matched your resume to jobs 
          and gave you a score, would you trust it? Why or why not?

CLOSED QUESTIONS (quantitative — used in charts below):
  IQ-S6. How long does your job search typically take before finding 
          a suitable opportunity?
          [ ] Less than 1 month  [ ] 1–3 months  [ ] 3–6 months  [ ] Over 6 months

  IQ-S7. On average, how many job applications do you submit per week?
          [ ] 1–2  [ ] 3–5  [ ] 6–10  [ ] More than 10

  IQ-S8. Have you ever been rejected without any feedback or explanation?
          [ ] Yes, always  [ ] Yes, sometimes  [ ] Rarely  [ ] Never

  IQ-S9. How would you rate your confidence in tailoring your resume 
          to match a specific job? (1 = Not confident, 5 = Very confident)
          Rating: ___

  IQ-S10. Would you use an automated system that scores your resume 
           against a job and tells you your match percentage before applying?
           [ ] Definitely Yes  [ ] Probably Yes  [ ] Not Sure  [ ] No
"""

# Responses for IQ-S6 — Job search duration (n=10)
search_duration = {
    "Less than\n1 month": 1,
    "1–3 months":         4,
    "3–6 months":         3,
    "Over 6 months":      2,
}

# Responses for IQ-S7 — Applications per week (n=10)
apps_per_week = {
    "1–2 apps":       2,
    "3–5 apps":       4,
    "6–10 apps":      3,
    "More than 10":   1,
}

# Responses for IQ-S8 — Rejected without feedback (n=10)
rejected_no_feedback = {
    "Yes, always":     4,
    "Yes, sometimes":  5,
    "Rarely":          1,
    "Never":           0,
}

# Responses for IQ-S9 — Resume tailoring confidence (1–5 scale, n=10 ratings)
tailoring_confidence = [2, 3, 3, 4, 2, 3, 4, 3, 2, 3]   # mean = 2.9

# Responses for IQ-S10 — Would use automated scoring (n=10)
use_auto_scoring = {
    "Definitely Yes":  6,
    "Probably Yes":    3,
    "Not Sure":        1,
    "No":              0,
}


# ─────────────────────────────────────────────
#  INTERVIEW: EMPLOYERS / HR RECRUITERS  (8 participants)
# ─────────────────────────────────────────────
"""
INTERVIEW GUIDE — EMPLOYERS / HR RECRUITERS
Conducted with: HR managers, recruiters at Pioneer Insurance Group
Format: Online, semi-structured, 20–30 minutes

OPEN-ENDED QUESTIONS (qualitative):
  IQ-E1. Describe your current resume screening process from 
          receiving applications to shortlisting candidates.
  IQ-E2. What are the biggest bottlenecks in your recruitment workflow?
  IQ-E3. How do you currently decide whether a candidate's resume 
          matches a job requirement?
  IQ-E4. Have you ever made a hiring decision that turned out to be 
          a poor match? What do you think caused it?
  IQ-E5. What information would you need from an AI scoring system 
          to trust its recommendations?

CLOSED QUESTIONS (quantitative):
  IQ-E6. How many resumes do you typically receive per job posting?
          [ ] Less than 20  [ ] 20–50  [ ] 50–100  [ ] Over 100

  IQ-E7. How long does it take to screen all applications for one posting?
          [ ] Less than 1 day  [ ] 1–3 days  [ ] 4–7 days  [ ] Over 1 week

  IQ-E8. Approximately what percentage of applications are qualified 
          for the role?
          [ ] Less than 10%  [ ] 10–25%  [ ] 26–50%  [ ] Over 50%

  IQ-E9. How often do promising candidates drop out due to slow 
          communication?
          [ ] Very often  [ ] Sometimes  [ ] Rarely  [ ] Never

  IQ-E10. How confident are you that your current screening process 
            identifies the best candidates? (1 = Not confident, 5 = Very confident)
            Rating: ___
"""

# Responses for IQ-E6 — Resumes per posting (n=8)
resumes_per_posting = {
    "Less than 20": 1,
    "20–50":        3,
    "50–100":       3,
    "Over 100":     1,
}

# Responses for IQ-E7 — Time to screen (n=8)
screening_time = {
    "Less than 1 day": 1,
    "1–3 days":        2,
    "4–7 days":        3,
    "Over 1 week":     2,
}

# Responses for IQ-E8 — % qualified (n=8)
pct_qualified = {
    "Less than 10%": 2,
    "10–25%":        4,
    "26–50%":        2,
    "Over 50%":      0,
}

# Responses for IQ-E9 — Candidates drop out (n=8)
candidate_dropout = {
    "Very often":  3,
    "Sometimes":   4,
    "Rarely":      1,
    "Never":       0,
}

# Responses for IQ-E10 — Screening confidence (1–5, n=8 ratings)
screening_confidence = [3, 2, 3, 4, 2, 3, 2, 3]   # mean = 2.75


# ══════════════════════════════════════════════════════════════════
#
#   PART B — QUESTIONNAIRE QUESTIONS & RESPONSES
#   (Distributed to wider group, Likert scale 1–5 used)
#   Seeker sample: n=30   Employer sample: n=20
#
# ══════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────
#  QUESTIONNAIRE: JOB SEEKERS  (n=30)
# ─────────────────────────────────────────────
"""
QUESTIONNAIRE — JOB SEEKERS
Distributed to: University students + recent graduates (n=30)
Format: Online Google Form

SECTION A — Current Recruitment Experience (Rate 1–5: 1=Strongly Disagree, 5=Strongly Agree)
  QS-S1.  The current job application process is time-consuming.
  QS-S2.  I find it difficult to know if my resume matches a job posting.
  QS-S3.  I receive timely feedback after submitting applications.
  QS-S4.  I understand why I was rejected after an unsuccessful application.
  QS-S5.  The recruitment process at companies I apply to is transparent.

SECTION B — System Acceptance (Rate 1–5)
  QS-S6.  I would trust an AI system to match my resume to a job.
  QS-S7.  An automated score out of 100 would help me decide which jobs to apply to.
  QS-S8.  I would feel comfortable uploading my resume to an online platform.
  QS-S9.  Receiving instant AI feedback on my application would reduce my anxiety.
  QS-S10. Email notifications about my application status are important to me.
"""

# Mean Likert scores per question (n=30, scale 1–5)
seeker_quest_labels = [
    "QS-S1\nProcess is\ntime-consuming",
    "QS-S2\nDifficult to\nmatch resume",
    "QS-S3\nTimely\nfeedback received",
    "QS-S4\nUnderstand\nrejection reason",
    "QS-S5\nProcess is\ntransparent",
    "QS-S6\nTrust AI\nmatching",
    "QS-S7\nScore helps\ndecision",
    "QS-S8\nComfort\nuploading resume",
    "QS-S9\nAI feedback\nreduces anxiety",
    "QS-S10\nEmail\nnotifications vital",
]
seeker_quest_means = [4.6, 4.2, 1.8, 1.9, 2.1, 3.8, 4.1, 3.9, 4.0, 4.5]

# Distribution of responses for selected question QS-S1 (n=30)
qs_s1_dist = {
    "1 – Strongly\nDisagree": 0,
    "2 – Disagree":           1,
    "3 – Neutral":            3,
    "4 – Agree":             10,
    "5 – Strongly\nAgree":   16,
}

# Distribution of responses for QS-S3 (feedback) — shows pain point
qs_s3_dist = {
    "1 – Strongly\nDisagree": 12,
    "2 – Disagree":           10,
    "3 – Neutral":             5,
    "4 – Agree":               2,
    "5 – Strongly\nAgree":     1,
}


# ─────────────────────────────────────────────
#  QUESTIONNAIRE: EMPLOYERS / HR  (n=20)
# ─────────────────────────────────────────────
"""
QUESTIONNAIRE — EMPLOYERS / HR RECRUITERS
Distributed to: HR recruiters, line managers at Pioneer Insurance Group (n=20)
Format: Online Google Form

SECTION A — Current Screening Process (Rate 1–5)
  QS-E1.  Manually screening resumes takes too much of my working time.
  QS-E2.  The quality of candidates shortlisted manually is consistently high.
  QS-E3.  We miss good candidates because of slow manual screening.
  QS-E4.  Our current process fairly evaluates all applicants.
  QS-E5.  We communicate with applicants in a timely manner.

SECTION B — System Adoption (Rate 1–5)
  QS-E6.  An AI system that scores resumes would save significant time.
  QS-E7.  I would trust the AI score when making shortlisting decisions.
  QS-E8.  Automatic email notifications to candidates would improve our process.
  QS-E9.  A dashboard showing applicant scores would help me prioritise reviews.
  QS-E10. I am concerned about AI bias in automated resume screening.
"""

employer_quest_labels = [
    "QS-E1\nScreening takes\ntoo much time",
    "QS-E2\nManual quality\nis consistent",
    "QS-E3\nMiss good\ncandidates",
    "QS-E4\nProcess is\nfair",
    "QS-E5\nTimely candidate\ncommunication",
    "QS-E6\nAI saves\nsignificant time",
    "QS-E7\nTrust AI\nscoring",
    "QS-E8\nAuto emails\nimprove process",
    "QS-E9\nDashboard helps\nprioritise",
    "QS-E10\nConcerned\nabout AI bias",
]
employer_quest_means = [4.5, 2.1, 4.0, 2.8, 2.3, 4.6, 3.4, 4.2, 4.5, 3.7]


# ══════════════════════════════════════════════════════════════════
#  CHART GENERATION FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def save(filename):
    plt.savefig(filename, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  Saved: {filename}")


# ─────────────────────────────────────────────
#  Chart 1 — Interview Seeker: Job Search Duration (bar)
# ─────────────────────────────────────────────
def chart_interview_seeker_duration():
    fig, ax = plt.subplots(figsize=(8, 5))
    keys   = list(search_duration.keys())
    values = list(search_duration.values())
    colors = [LBLUE if v < max(values) else BLUE for v in values]
    bars = ax.bar(keys, values, color=colors, edgecolor="white", width=0.5)
    ax.set_title("IQ-S6: How long does your job search typically take?\n(Interview Responses, n=10)",
                 fontsize=13, fontweight="bold", color=BLUE, pad=14)
    ax.set_ylabel("Number of Respondents", fontsize=11)
    ax.set_ylim(0, max(values) + 1.5)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(v), ha="center", va="bottom", fontweight="bold", fontsize=12)
    ax.tick_params(axis="x", labelsize=10)
    fig.tight_layout()
    save("chart1_interview_seeker_duration.png")


# ─────────────────────────────────────────────
#  Chart 2 — Interview Seeker: Would use auto scoring (pie)
# ─────────────────────────────────────────────
def chart_interview_seeker_auto():
    fig, ax = plt.subplots(figsize=(7, 7))
    labels = list(use_auto_scoring.keys())
    sizes  = list(use_auto_scoring.values())
    colors = [GREEN, LGREEN, AMBER, RED]
    explode = (0.06, 0, 0, 0)
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, explode=explode,
        autopct=lambda p: f"{p:.0f}%\n({int(round(p*sum(sizes)/100))})",
        startangle=140, textprops={"fontsize": 11},
        wedgeprops={"edgecolor": "white", "linewidth": 2}
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
    ax.set_title("IQ-S10: Would you use automated resume scoring?\n(Interview Responses, n=10)",
                 fontsize=13, fontweight="bold", color=BLUE, pad=18)
    save("chart2_interview_seeker_auto_scoring.png")


# ─────────────────────────────────────────────
#  Chart 3 — Interview Employer: Screening Time (horizontal bar)
# ─────────────────────────────────────────────
def chart_interview_employer_screening_time():
    fig, ax = plt.subplots(figsize=(8, 5))
    keys   = list(screening_time.keys())
    values = list(screening_time.values())
    y      = range(len(keys))
    colors = [RED if v == max(values) else LBLUE for v in values]
    bars   = ax.barh(list(y), values, color=colors, edgecolor="white", height=0.5)
    ax.set_yticks(list(y))
    ax.set_yticklabels(keys, fontsize=11)
    ax.set_xlabel("Number of Respondents", fontsize=11)
    ax.set_xlim(0, max(values) + 1.5)
    ax.set_title("IQ-E7: How long does it take to screen all applications?\n(Interview Responses, n=8)",
                 fontsize=13, fontweight="bold", color=BLUE, pad=14)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                str(v), va="center", fontweight="bold", fontsize=12)
    fig.tight_layout()
    save("chart3_interview_employer_screening_time.png")


# ─────────────────────────────────────────────
#  Chart 4 — Interview Employer: % Qualified (donut)
# ─────────────────────────────────────────────
def chart_interview_employer_qualified():
    fig, ax = plt.subplots(figsize=(7, 7))
    labels = list(pct_qualified.keys())
    sizes  = list(pct_qualified.values())
    colors = [RED, AMBER, LGREEN, GREEN]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct=lambda p: f"{p:.0f}%\n({int(round(p*sum(sizes)/100))})" if p > 0 else "",
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 2, "width": 0.6},
        textprops={"fontsize": 11}
    )
    for at in autotexts:
        at.set_fontweight("bold")
        at.set_fontsize(11)
    ax.set_title("IQ-E8: What % of applications are typically qualified?\n(Interview Responses, n=8)",
                 fontsize=13, fontweight="bold", color=BLUE, pad=18)
    # centre label
    ax.text(0, 0, "Most\napplicants\nunqualified",
            ha="center", va="center", fontsize=10, fontweight="bold", color=RED)
    save("chart4_interview_employer_pct_qualified.png")


# ─────────────────────────────────────────────
#  Chart 5 — Questionnaire Seeker: Mean Likert Scores (horizontal bar)
# ─────────────────────────────────────────────
def chart_quest_seeker_means():
    fig, ax = plt.subplots(figsize=(10, 7))
    y      = range(len(seeker_quest_labels))
    colors = [BLUE if m >= 3.5 else (AMBER if m >= 2.5 else RED)
              for m in seeker_quest_means]
    bars   = ax.barh(list(y), seeker_quest_means,
                     color=colors, edgecolor="white", height=0.6)
    ax.set_yticks(list(y))
    ax.set_yticklabels(seeker_quest_labels, fontsize=9)
    ax.set_xlabel("Mean Score  (1 = Strongly Disagree → 5 = Strongly Agree)", fontsize=10)
    ax.set_xlim(0, 5.5)
    ax.axvline(x=3, color=GREY, linestyle="--", linewidth=1, label="Neutral (3.0)")
    for bar, v in zip(bars, seeker_quest_means):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                f"{v:.1f}", va="center", fontweight="bold", fontsize=10)
    ax.set_title("Questionnaire — Job Seekers: Mean Likert Responses\n(n=30, Scale 1–5)",
                 fontsize=13, fontweight="bold", color=BLUE, pad=14)
    ax.legend(fontsize=9)
    # colour legend
    patches = [
        mpatches.Patch(color=BLUE,  label="Mean ≥ 3.5 (Agreement)"),
        mpatches.Patch(color=AMBER, label="Mean 2.5–3.4 (Neutral)"),
        mpatches.Patch(color=RED,   label="Mean < 2.5 (Disagreement)"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=9)
    fig.tight_layout()
    save("chart5_quest_seeker_means.png")


# ─────────────────────────────────────────────
#  Chart 6 — Questionnaire Employer: Mean Likert Scores (horizontal bar)
# ─────────────────────────────────────────────
def chart_quest_employer_means():
    fig, ax = plt.subplots(figsize=(10, 7))
    y      = range(len(employer_quest_labels))
    colors = [BLUE if m >= 3.5 else (AMBER if m >= 2.5 else RED)
              for m in employer_quest_means]
    bars   = ax.barh(list(y), employer_quest_means,
                     color=colors, edgecolor="white", height=0.6)
    ax.set_yticks(list(y))
    ax.set_yticklabels(employer_quest_labels, fontsize=9)
    ax.set_xlabel("Mean Score  (1 = Strongly Disagree → 5 = Strongly Agree)", fontsize=10)
    ax.set_xlim(0, 5.5)
    ax.axvline(x=3, color=GREY, linestyle="--", linewidth=1)
    for bar, v in zip(bars, employer_quest_means):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                f"{v:.1f}", va="center", fontweight="bold", fontsize=10)
    ax.set_title("Questionnaire — Employers / HR: Mean Likert Responses\n(n=20, Scale 1–5)",
                 fontsize=13, fontweight="bold", color=BLUE, pad=14)
    patches = [
        mpatches.Patch(color=BLUE,  label="Mean ≥ 3.5 (Agreement)"),
        mpatches.Patch(color=AMBER, label="Mean 2.5–3.4 (Neutral)"),
        mpatches.Patch(color=RED,   label="Mean < 2.5 (Disagreement)"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=9)
    fig.tight_layout()
    save("chart6_quest_employer_means.png")


# ─────────────────────────────────────────────
#  Chart 7 — Seeker QS-S1 Distribution (stacked bar)
# ─────────────────────────────────────────────
def chart_qs_s1_distribution():
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = list(qs_s1_dist.keys())
    vals   = list(qs_s1_dist.values())
    colors = [RED, "#ef5350", AMBER, LGREEN, GREEN]
    bars   = ax.bar(labels, vals, color=colors, edgecolor="white", width=0.55)
    ax.set_title("QS-S1: 'The current job application process is time-consuming'\n"
                 "(Questionnaire Response Distribution, n=30)",
                 fontsize=12, fontweight="bold", color=BLUE, pad=14)
    ax.set_ylabel("Number of Respondents", fontsize=11)
    ax.set_ylim(0, max(vals) + 3)
    for bar, v in zip(bars, vals):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    str(v), ha="center", fontweight="bold", fontsize=13)
    ax.tick_params(axis="x", labelsize=9)
    fig.tight_layout()
    save("chart7_qs_s1_distribution.png")


# ─────────────────────────────────────────────
#  Chart 8 — Seeker QS-S3 Distribution (pain point)
# ─────────────────────────────────────────────
def chart_qs_s3_distribution():
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = list(qs_s3_dist.keys())
    vals   = list(qs_s3_dist.values())
    colors = [RED, "#ef5350", AMBER, LGREEN, GREEN]
    bars   = ax.bar(labels, vals, color=colors, edgecolor="white", width=0.55)
    ax.set_title("QS-S3: 'I receive timely feedback after submitting applications'\n"
                 "(Questionnaire Response Distribution, n=30) — KEY PAIN POINT",
                 fontsize=12, fontweight="bold", color=RED, pad=14)
    ax.set_ylabel("Number of Respondents", fontsize=11)
    ax.set_ylim(0, max(vals) + 3)
    for bar, v in zip(bars, vals):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    str(v), ha="center", fontweight="bold", fontsize=13)
    ax.tick_params(axis="x", labelsize=9)
    # annotation arrow
    ax.annotate("22 of 30 respondents\ndisagree they get feedback",
                xy=(0.5, 12), xytext=(2.5, 13),
                arrowprops=dict(arrowstyle="->", color=RED),
                fontsize=10, color=RED, fontweight="bold")
    fig.tight_layout()
    save("chart8_qs_s3_pain_point.png")


# ─────────────────────────────────────────────
#  Chart 9 — Combined Side-by-Side Summary
# ─────────────────────────────────────────────
def chart_combined_summary():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Seeker top 5 pain points
    ax = axes[0]
    items  = ["Process is\ntime-consuming", "Difficult to\nmatch resume",
              "Timely feedback\nnot received", "Rejection reason\nunknown",
              "Would use\nAI scoring"]
    scores = [4.6, 4.2, 1.8, 1.9, 3.8]
    colors = [BLUE, BLUE, RED, RED, GREEN]
    y = range(len(items))
    ax.barh(list(y), scores, color=colors, edgecolor="white", height=0.5)
    ax.set_yticks(list(y))
    ax.set_yticklabels(items, fontsize=10)
    ax.set_xlim(0, 5.5)
    ax.axvline(x=3, color=GREY, linestyle="--", linewidth=1)
    ax.set_xlabel("Mean Score (1–5)", fontsize=10)
    ax.set_title("Job Seekers — Key Findings\n(n=30)", fontsize=12,
                 fontweight="bold", color=BLUE)
    for i, v in enumerate(scores):
        ax.text(v + 0.05, i, f"{v}", va="center", fontweight="bold", fontsize=10)

    # Right: Employer top 5 findings
    ax2 = axes[1]
    items2  = ["Screening takes\ntoo much time", "Miss good\ncandidates",
               "AI saves time", "Dashboard helps\nprioritise",
               "Concerned about\nAI bias"]
    scores2 = [4.5, 4.0, 4.6, 4.5, 3.7]
    colors2 = [RED, RED, GREEN, GREEN, AMBER]
    y2 = range(len(items2))
    ax2.barh(list(y2), scores2, color=colors2, edgecolor="white", height=0.5)
    ax2.set_yticks(list(y2))
    ax2.set_yticklabels(items2, fontsize=10)
    ax2.set_xlim(0, 5.5)
    ax2.axvline(x=3, color=GREY, linestyle="--", linewidth=1)
    ax2.set_xlabel("Mean Score (1–5)", fontsize=10)
    ax2.set_title("Employers / HR — Key Findings\n(n=20)", fontsize=12,
                  fontweight="bold", color=BLUE)
    for i, v in enumerate(scores2):
        ax2.text(v + 0.05, i, f"{v}", va="center", fontweight="bold", fontsize=10)

    patches = [
        mpatches.Patch(color=BLUE,  label="Pain point (high agreement)"),
        mpatches.Patch(color=RED,   label="Critical gap / problem"),
        mpatches.Patch(color=GREEN, label="System benefit agreed"),
        mpatches.Patch(color=AMBER, label="Neutral / concern"),
    ]
    fig.legend(handles=patches, loc="lower center", ncol=4, fontsize=9,
               bbox_to_anchor=(0.5, -0.05))
    fig.suptitle("Pioneer Insurance Group Job Matching System\n"
                 "Data Collection Summary — Interviews + Questionnaires",
                 fontsize=13, fontweight="bold", color=BLUE, y=1.02)
    fig.tight_layout()
    save("chart9_combined_summary.png")


# ══════════════════════════════════════════════════════════════════
#  RUN ALL CHARTS
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\nGenerating all Chapter 3 research charts...\n")
    chart_interview_seeker_duration()          # Chart 1
    chart_interview_seeker_auto()             # Chart 2
    chart_interview_employer_screening_time() # Chart 3
    chart_interview_employer_qualified()      # Chart 4
    chart_quest_seeker_means()               # Chart 5
    chart_quest_employer_means()             # Chart 6
    chart_qs_s1_distribution()              # Chart 7
    chart_qs_s3_distribution()              # Chart 8
    chart_combined_summary()                # Chart 9
    print("\nAll 9 charts saved to current folder.")
    print("Use them in Chapter 3 sections 3.4.1 and 3.4.2")