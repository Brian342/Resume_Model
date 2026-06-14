"""
Models.py - Pydantic Schemas for JobMatch API
===============================================================
These define the shape of every request body and response in the API.
FastAPI uses these to:
    -Validate incoming JSON automatically
    -Generate the /docs Swagger UI
    -Serialize outgoing responses
    
PATTERN:
    -*Create -> What the client sends when creating something (no id, no timestamps)
    -*Update -> WHat the client sends when editing (all fields optional)
    -*Out -> What the API returns (Includes id, timestamps, computed fields)
    -*Token -> auth-related payloads
    
Roles (mirrors Your SQLite app):
    -"Seeker" -> Job Seekers who browse and apply
    -"employer"-> Companies that post jobs and review applicants 
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    seeker = "seeker"
    employer = "employer"

class ApplicationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class UserCreate(BaseModel):
    """
    Sent by client when registering a new account.
    Mirrors do_signup() in app.py
    """
    full_name:str
    email: EmailStr
    password: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v
    
    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()
    
class UserLogin(BaseModel):
    """Sent by client on the login form"""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """
    Returned after Login / register and in profile endpoints.
    Never includes the password hash
    """
    id: int
    full_name: str
    email: str
    role: UserRole
    job_categories: Optional[str] = None 
    job_keywords: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    """Returned after a successful login"""
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenDate(BaseModel):
    """Decoded payload stored inside the JWT."""
    user_id: int
    role: UserRole


# JOB SCHEMAS
class JobCreated(BaseModel):
    """"Sent by an employer when posting a new job
    Mirrors created_job() in db.py
    """

    title: str
    company: str
    location: str
    description: str
    requirements: str
    salary: Optional[str] = ""

    @field_validator("title", "company", "location", "description", "requirements")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field cannot be empty")
        return v.strip()
    
class JobUpdate(BaseModel):
    """Sent by an employer when editing an existing job.
    All fields optional - only provided fields will be updated
    """
    title: Optional[str] = None
    company:      Optional[str] = None
    location:     Optional[str] = None
    description:  Optional[str] = None
    requirements: Optional[str] = None
    salary:       Optional[str] = None
    is_active:    Optional[bool] = None
 
 
class JobOut(BaseModel):
    """
    Returned when listing or viewing a job.
    Includes employer name (from JOIN in db.py).
    """
    id:            int
    employer_id:   int
    employer_name: Optional[str] = None   # populated from JOIN query
    title:         str
    company:       str
    location:      str
    description:   str
    requirements:  str
    salary:        Optional[str] = None
    is_active:     bool
    created_at:    datetime
 
    model_config = {"from_attributes": True}
 
 

 
class ApplicationCreate(BaseModel):
    """
    Sent when a seeker submits an application.
    resume_path is set server-side after the file is saved.
    answers is a JSON string of screener question answers.
    Mirrors create_application() in db.py.
    """
    job_id:  int
    answers: Optional[str] = "{}"   # JSON string, default empty object
 
 
class ApplicationStatusUpdate(BaseModel):
    """Sent by an employer to approve / reject an application."""
    status: ApplicationStatus
 
 
class ApplicationScoreUpdate(BaseModel):
    """
    Internal schema — used by the ML matching route
    to write ai_score + ml_label back to the application.
    Mirrors update_application_score() in db.py.
    """
    ai_score: float
    ml_label: str
 
 
class ApplicationOut(BaseModel):
    """
    Returned when listing applications.
    Includes joined fields from both the jobs and users tables.
    """
    id:          int
    job_id:      int
    seeker_id:   int
 
    # Joined from jobs table (visible to seeker)
    job_title:   Optional[str] = None
    company:     Optional[str] = None
    location:    Optional[str] = None
 
    # Joined from users table (visible to employer)
    seeker_name:  Optional[str] = None
    seeker_email: Optional[str] = None
 
    resume_path: Optional[str] = None
    answers:     Optional[str] = None
 
    # ML / AI fields
    ai_score:   Optional[float] = None
    ml_label:   Optional[str]  = None
 
    status:     ApplicationStatus
    applied_at: datetime
 
    model_config = {"from_attributes": True}
 
 

 
class PreferencesUpdate(BaseModel):
    """
    Sent by a seeker to save their job category and keyword preferences.
    Mirrors save_seeker_preferences() in db.py.
    """
    categories: List[str]   # e.g. ["Technology & Software", "Data Science & AI"]
    keywords:   List[str]   # e.g. ["python", "machine learning"]
 
 
class PreferencesOut(BaseModel):
    """Returned when fetching a seeker's saved preferences."""
    categories: List[str]
    keywords:   List[str]
 
 

 
class MatchRequest(BaseModel):
    """
    Sent to the /match endpoint to score a resume against a job.
    Either provide resume text directly or reference an existing application.
    """
    application_id: Optional[int] = None   # score an already-uploaded resume
    resume_text:    Optional[str] = None   # or pass raw text directly
    job_id:         int
 
 
class MatchResult(BaseModel):
    """Returned by the /match endpoint."""
    application_id: Optional[int] = None
    job_id:         int
    ai_score:       float          # 0-100
    ml_label:       str            # "Qualified" / "Not Qualified" / "Review Needed"
    details:        Optional[str] = None   # human-readable explanation
 
 
 
class MessageResponse(BaseModel):
    """Simple success/info message wrapper."""
    message: str
 

