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
from ..import db
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

