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
