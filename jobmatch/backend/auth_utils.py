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
