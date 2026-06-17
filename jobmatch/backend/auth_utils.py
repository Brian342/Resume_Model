"""
auth_utils.py - Password Hashing & JWT Token Logic
This replaces the bcrypt calls that lived directly in app.py
(hash_password / verify_password) and adds jwt token creation/verification,
since a REST API needs stateless auth instead of streamlit's session_state.

HOW LOGIN WORKS NOW (vs. the old Streamlit flow):
  OLD (Streamlit):
    1. User submits login form
    2. do_login() checks password, then writes user info into
       st.session_state — which persists because Streamlit keeps
       the same Python process alive per browser tab.

  NEW (FastAPI):
    1. Client POSTs /auth/login with email + password
    2. We verify the password hash (same bcrypt check as before)
    3. We create a JWT ("JSON Web Token") containing the user's id + role
    4. Client stores that token (e.g. in localStorage) and sends it
       in the Authorization header on every future request
    5. get_current_user() decodes that token on each request to know
       who's calling — this replaces st.session_state entirely.

JWT is just a signed, tamper-proof string. We don't store sessions in the
database — anyone with a valid signature is trusted, until the token expires.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

import db
from models import TokenDate, UserRole

load_dotenv()

# CONFIG (read from .env)

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 hours default

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. check your jobmatch/backend/.env file."
    )

# This tells FastAPI's Swagger docs where to send the login request,
# and how to extract the "Bearer <token>" header on protected routes.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# PASSWORD HASHING
# Mirrors hash_password() / verify_password() from the original app.py,
# using bcrypt directly (same library, same behavior — no passlib).

def hash_password(plain_password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.
    Returns a string safe to store in the database.
    """
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Returns True if plain_password matches the stored bcrypt hash.
    Identical logic to the original app.py verify_password().
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Malformed hash in the database - treat as no match rather than crash
        return False

# JWT TOKEN CREATION
def create_access_token(user_id: int, role: str) -> str:

