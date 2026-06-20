"""
main.py — FastAPI Entry Point for JobMatch
=============================================
This is the REST equivalent of app.py's role as Streamlit's entry point —
but instead of rendering pages and routing between them via
st.session_state["current_page"], it wires together the API routers
and exposes them as HTTP endpoints for the React frontend to call.

WHAT THIS FILE DOES:
  1. Creates the FastAPI app instance
  2. On startup: connects to PostgreSQL + creates tables if missing
     (mirrors db.create_table() running automatically at the bottom
     of the original db.py on import)
  3. On shutdown: cleanly closes the database connection pool
  4. Configures CORS so the React frontend (running on a different
     port during development) is allowed to call this API
  5. Registers all four routers: auth, jobs, applications, match
  6. Adds a simple health-check route

RUN THE SERVER:
  cd jobmatch/backend
  uvicorn main:app --reload --port 8000

Then visit http://localhost:8000/docs for the interactive Swagger UI —
this replaces manually clicking through the Streamlit app to test things.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import db
from routers import auth, jobs, applications, match

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# LIFESPAN — startup / shutdown hooks
# Replaces db.py's old "create_table() runs automatically on import"
# pattern with an explicit, controlled startup sequence.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting JobMatch API...")
    db.create_tables()
    await db.connect()

    yield

    await db.disconnect()
    print("JobMatch API shut down cleanly...")


# APP INSTANCE
app = FastAPI(
    title="JobMatch API",
    description=(
        "REST API for the JobMatch platform - job seekers browse and apply "
        "to jobs with AI-powered resume screening: employers post jobs and "
        "review ML-scored applicants"
    ),
    version="1.0.0",
    lifespan=lifespan,
)
# CORS
# Without this, the React frontend (e.g. http://localhost:5173) would be
# blocked by the browser from calling this API (e.g. http://localhost:8000)
# since they're on different ports — browsers treat that as a different origin.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# ROUTERS
# Each router's endpoints get prefixed automatically based on the
# prefix set inside that router file (e.g. auth.router has prefix="/auth").

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(match.router)


# HEALTH CHECK
# Simple route to verify the server + database are up.
# Useful for quick manual checks and for deployment health checks.
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "service": "JobMatch API",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
        Verifies the database connection is actually alive,
        not just that the server process is running.
        """
    try:
        await db.database.fetch_one("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "database": db_status,
    }
