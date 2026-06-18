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
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from ..import db
from ..auth_utils import get_current_user, require_employer, require_seeker
from ..models import ApplicationOut, ApplicationStatusUpdate, MessageResponse

router = APIRouter(prefix="/applications", tags=["Applications"])

# ML MODEL LOADING  (mirrors the top of apply.py)

