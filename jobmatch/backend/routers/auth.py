"""
routers/auth.py — Registration & Login Endpoints
This is the REST equivalent of show_login_page() / show_signup_page() /
do_login() / do_signup() from the original app.py.

ENDPOINTS:
  POST /auth/register   → create a new account (seeker or employer)
  POST /auth/login      → verify credentials, return a JWT
  GET  /auth/me         → return the currently logged-in user's profile

FLOW DIFFERENCE FROM STREAMLIT:
  Old: do_signup() / do_login() wrote directly into st.session_state.
  New: register/login return a JWT in the response body. The client
       (React frontend) stores it and attaches it to future requests
       via the Authorization: Bearer <token> header.
"""

from fastapi import APIRouter, HTTPException, Depends, status

import db
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from models import UserCreate, UserLogin, UserOut, Token, MessageResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


# REGISTER
# Mirrors do_signup() in app.py

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new seeker or employer account",
)
async def register(user_in: UserCreate):
    """
    Validates and creates a new user account.

    Validation (full_name not empty, password >= 6 chars) already happened
    in models.py via Pydantic validators — by the time we get here,
    user_in is guaranteed to be well-formed.

    The only thing left to check here is whether the email is already taken,
    which we only find out by attempting the insert (mirrors the original
    sqlite3.IntegrityError handling in db.create_user()).
    """
    hashed = hash_password(user_in.password)

    success = await db.create_user(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=hashed,
        role=user_in.role.value,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    return MessageResponse(message="Account created successfully. please log in.")

# LOGIN
# Mirrors do_login() in app.py
