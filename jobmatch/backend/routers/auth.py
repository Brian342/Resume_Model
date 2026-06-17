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

from .. import db
from ..auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from ..models import UserCreate, UserLogin, UserOut, Token, MessageResponse

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

@router.post(
    "/login",
    response_model=Token,
    summary="Log in and receive a JWT access token",
)
async def login(credentials: UserLogin):
    """
    Verifies email + password, then returns a JWT the client will use
    for all future authenticated requests.

    Mirrors do_login(): looks up by email, checks the bcrypt hash,
    and rejects with the same two failure cases —
    'no account found' and 'incorrect password' — but combined into one
    generic message, since revealing *which* part failed helps attackers
    enumerate valid emails.
    """
    user = await db.get_user_by_email(credentials.email)

    if user is None or not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"www-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user["id"], role=user["role"])

    return Token(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


# CURRENT USER PROFILE
# Used by the React frontend on page load to check "am I logged in,
# and as who?" — replaces reading st.session_state directly.

@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the currently authenticated user's profile",
)
async def read_current_user(current_user: dict = Depends(get_current_user)):
    """
    Returns the profile of whoever's token was sent in the
    Authorization header. The frontend calls this on app load to
    restore the logged-in state after a page refresh.
    """
    return UserOut.model_validate(current_user)
