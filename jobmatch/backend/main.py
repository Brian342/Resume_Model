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

import bd
from routers import auth, jobs, applications, match

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# LIFESPAN — startup / shutdown hooks
# Replaces db.py's old "create_table() runs automatically on import"
# pattern with an explicit, controlled startup sequence.