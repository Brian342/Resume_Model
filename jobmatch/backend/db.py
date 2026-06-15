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

