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
