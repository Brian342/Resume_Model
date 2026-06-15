"""
db.py - PostgreSQL Database Layer for JobMatch

This is a full rewrite of the original SQLite db.py, ported to PostgreSQL
using the 'databases' library for async query execution (required by FastAPI)
and 'sqlalchemy' core for schema definition

Works:
  - 'databases'  → async query runner (SELECT, INSERT, UPDATE, DELETE)
  - 'sqlalchemy' → defines table structure + creates them via metadata.create_all()
  - We never use SQLAlchemy ORM — just Core, so queries stay readable SQL.
 
STARTUP FLOW (called from main.py):
  1. connect()        → opens the async DB connection pool
  2. create_tables()  → runs CREATE TABLE IF NOT EXISTS for all 3 tables
  3. On shutdown: disconnect() closes the pool cleanly
 
ALL FUNCTIONS mirror the original SQLite db.py exactly —
same names, same parameters, same return shapes — so the rest of the
app can call them identically. Only the internals changed (async + PostgreSQL).
 
ENVIRONMENT:
  Reads DATABASE_URL from .env via python-dotenv.
  Format: postgresql://jobmatch_user:jobmatch_pass123@localhost:5432/jobmatch_db
"""
import os
import json
from datetime import datetime
from typing import Optional

import databases
import sqlalchemy
from dotenv import load_dotenv

load_dotenv()  # read .env file for DATABASE_URL

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. "
                     "Check your jobmatch/backend/.env file."
                     )

# 'databases' uses an async connection pool.
# min_size / max_size control how many PostgreSQL connections stay open.
database = databases.Database(
    DATABASE_URL,
    min_size=2,
    max_size=10
)

# SQLAlchemy metadata holds all table definitions.
# We call metadata.create_all(engine) once at startup to create missing tables.
metadata = sqlalchemy.MetaData()

# TABLE DEFINITIONS
# Mirrors the CREATE TABLE statements in the original db.py exactly.
# Column names, types, constraints, and defaults are preserved.

users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_keys=True, autoincrement=True),
    sqlalchemy.Column("full_name", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("email", sqlalchemy.Text, nullable=False, unique=True),
    sqlalchemy.Column("password", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("role", sqlalchemy.Text, nullable=False),  # seeker employer
    sqlalchemy.Column("job_categories", sqlalchemy.Text, nullable=True, default=""),
    sqlalchemy.Column("job_keywords", sqlalchemy.Text, nullable=True, default=""),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

jobs = sqlalchemy.Table(
    "jobs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("employer_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("title", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("company", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("location", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("description", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("requirements", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("salary", sqlalchemy.Text, nullable=True, default=""),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

applications = sqlalchemy.Table(
    "applications",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("job_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("jobs.id"), nullable=False),
    sqlalchemy.Column("seeker_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("resume_path", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("answers", sqlalchemy.Text, nullable=True, default="{}"),
    sqlalchemy.Column("ai_score", sqlalchemy.Float, nullable=True),
    sqlalchemy.Column("ml_label", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("status", sqlalchemy.Text, nullable=False, default="pending"),  # pending|approved|rejected
    sqlalchemy.Column("applied_at", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.UniqueConstraint("job_id", "seeker_id", name="uq_job_seeker"),
)


# StartUp / Shutdown (Called from main.py lifespan)
async def connect():
    """Opens the async database connection pool."""
    await database.connect()
    print("Database connected.")


async def disconnect():
    """Closes the async database connection pool."""
    await database.disconnect()
    print("Database disconnected")


def create_tables():
    """
    Runs CREATE TABLE IF NOT EXISTS for all tables.
    Uses a synchronous SQLAlchemy engine - only called once at startup
    """
    sync_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
    engine = sqlalchemy.create_engine(sync_url)
    metadata.create_all(engine)
    engine.dispose()
    print("Tables created (or already exist).")


# USER FUNCTIONS
# Mirrors: create_user, get_user_by_email, get_user_by_id

async def create_user(full_name: str, email: str, password_hash: str, role: str) -> bool:
    """
    Inserts a new user. Returns True on success, False if email already exists.
    password_hash must already be hashed before calling this (done in auth_utils.py)
    """
    query = users.insert().values(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        password=password_hash,
        role=role,
        job_categories="",
        job_keywords="",
        created_at=datetime.utcnow(),
    )
    try:
        await database.execute(query)
        return True
    except Exception:
        # Unique constraint on emial violated - email already registered
        return False


async def get_user_by_email(email: str) -> Optional[dict]:
    """
    Fetches a single user by email. Used during login.
    Returns a dict or None if not found
    """
    query = users.select().where(
        users.c.email == email.strip().lower()
    )
    row = await database.fetch_one(query)
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Fetches a user by their ID. Used to display profile info."""
    query = users.select().where(users.c.id == user_id)
    row = await database.fetch_one(query)
    return dict(row) if row else None


# JOB FUNCTIONS
# Mirrors: create_job, get_all_active_jobs, get_jobs_by_employer,
#          get_job_by_id, toggle_job_active, update_job, delete_job

async def create_job(
        employer_id: int,
        title: str,
        company: str,
        location: str,
        description: str,
        requirements: str,
        salary: str = ""
) -> int:
    """Inserts a new Job Posting. Returns the new job's ID.
    Called from routers/jobs.py when an employer posts a job
    """
    query = jobs.insert().values(
        employer_id=employer_id,
        title=title,
        company=company,
        location=location,
        description=description,
        requirements=requirements,
        salary=salary,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    job_id = await database.execute(query)
    return job_id

async def get_all_active_jobs(
        categories: Optional[str] = None,
        keywords: Optional[str] = None
) -> list:
    """
    Fetches all active jobs, joined with the employer's name.
    Optionally filters by the seeker's saved category/keyword preferences.

    categories: comma-separated string e.g "Technology & Software, Data Science & AI"
    keywords: comma-separated string e.g "python, machine learning"

    Mirrors the JOIN query in the original get_all_active_jobs().
    """
    # Base JOIN - jobs + employer name (same as original SQLite Query)
    j = jobs.alias("j")
    u = users.alias("u")
    query = (
        sqlalchemy.select(
            j,
            u.c.full_name.label("employer_name"),
        )
        .select_from(j.join(u, j.c.employer_id == u.c.id))
        .where(j.c.is_active == True)
        .order_by(j.c.created_at.desc())
    )

    rows = await database.fetch_all(query)
    result = [dict(r) for r in rows]

    # Apply preference filters in Python (simple + portable)
    if categories:
        cat_list = [c.strip().lower() for c in categories.split(",") if c.strip()]
        if cat_list:
            result = [
                r for r in result
                if any(
                    cat in (r["title"] + " " + r["description"] + " " + r["requirements"]).lower()

                    for cat in cat_list
                )
            ]

    if keywords:
        kw_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        if kw_list:
            result = [
                r for r in result
                if any(
                    kw in (r["title"] + " " + r["description"] + " " + r["requirements"]).lower()

                    for kw in kw_list

                )
            ]

    return result


