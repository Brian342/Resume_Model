"""
app.py — Entry Point for the Resume Screening System
=====================================================
This is the FIRST file Streamlit runs when you start the app.
It handles:
  1. Session state setup — remembering who is logged in
  2. Login page — verify email + password
  3. Signup page — register as seeker or employer
  4. Routing — send user to the right dashboard

HOW it WORKS:
  Streamlit re-runs this ENTIRE script from top to bottom every time
  the user clicks a button or types something. This is why we use
  st.session_state — it persists data between this re-runs.

  Session_state is like a backpack the user carries around.
  Once they log in, we put their info in the backpack so every page
  can read it without asking the database again.

RUN THE APP:
  streamlit run app.py

INSTALL REQUIREMENTS FIRST:
  pip installs streamlit bcrypt
"""

import streamlit as st
import bcrypt
from db import get_user_by_email, create_user
from employer_dashboard import show_employer_dashboard
from seeker_dashboard import show_seeker_dashboard
from apply import show_apply_page
from db import save_seeker_preferences, get_seeker_preferences

# Page Configuration
st.set_page_config(
    page_title="Pioneer Insurance Group Job Match",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Global Style
st.markdown("""
    <style>
        /* Hide the default Streamlit top menu and footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
 
        /* Make the main container a bit narrower and centered */
        .block-container {
            padding-top: 2rem;
            max-width: 900px;
        }
 
        /* Style for our custom card-like containers */
        .auth-box {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid #e0e0e0;
        }
 
        /* Make the role selector pills look nicer */
        div[data-testid="stRadio"] > div {
            flex-direction: row;
            gap: 1rem;
        }
    </style>
""", unsafe_allow_html=True)


# Session State Initialisation
def init_session_state():
    defaults = {
        "logged_in": False,
        "user_id": None,
        "user_name": None,
        "user_email": None,
        "role": None,
        "auth_page": "login",  # starts o the login form by default
        "current_page": "home"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# Password Helpers
def hash_password(plain_password: str) -> str:
    """Hashes a plain-text password using bcrypt. Returns a string."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")  # Store as String in SQLite


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Returns True if plain_password matches the stored hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# This is a comment
# Login Logic
def do_login(email: str, password: str):
    """
    Looks up the user by email, verifies their password,
    and populates session_state if correct.

    This function is called when the login button is clicked.
    it does Not Display anything - it only updates state.
    The UI re-runs after this and shows the dashboard.
    """

    user = get_user_by_email(email.strip().lower())

    if user is None:
        return False, "No account found with that email."

    if not verify_password(password, user["password"]):
        return False, "Incorrect password."

    # Credentials are correct - populate session state
    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["user_name"] = user["full_name"]
    st.session_state["user_email"] = user["email"]
    st.session_state["role"] = user["role"]

    return True, "Login successful."


# Signup Logic

def do_signup(full_name: str, email: str, password: str, role: str):
    """
    Validates Inputs and creates a new user account.

    Returns (success: bool, message: str)
    """
    # Basic Validation - never trust user input
    if not full_name.strip():
        return False, "Please enter your full name."
    if "@" not in email or "." not in email:
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters"

    hashed = hash_password(password)
    success = create_user(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        password_hash=hashed,
        role=role
    )

    if not success:
        return False, "An account with that email already exists."

    return True, "Account Created: Please Log In."


# LogOut
def do_logout():
    """
    Clears all session states and returns users to the login screen.
    Called when the user clicks the Logout button in the sidebar
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()  # Re-set defaults so the app doesn't break
    st.rerun()  # Force the page to reload immediately


# Login Page UI
def show_login_page():
    """Renders the Login Form."""

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## JobMatch")
        st.markdown("##### Pioneer Insurance Group Job Match Platform")
        st.divider()

        st.markdown("### Sign in to your account")

        # st.text_input returns whatever the user typed as a string
        email = st.text_input("Email address", placeholder="you@example.com", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        # type="password" hides the characters as the user types

        # st.button returns True only on the frame the user clicks it
        if st.button("Log in", use_container_width=True, type="primary"):
            if not email or not password:
                st.warning("Please fill in all fields!!")
            else:
                success, message = do_login(email, password)
                if success:
                    st.success(message)
                    st.rerun()  # Re-run the script - now logged_in=True, shows dashboard

                else:
                    st.error(message)

        st.divider()
        st.markdown("Don't have an account?")
        if st.button("Create an account", use_container_width=True):
            st.session_state["auth_page"] = "signup"
            st.rerun()


# Signup Page UI
def show_signup_page():
    """Renders the registration form."""

    col1, col2, clo3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## 🧳 JobMatch")
        st.markdown("##### Pioneer Insurance Group Job Match Platform")
        st.divider()

        st.markdown("### Create your account")

        full_name = st.text_input("Full name", placeholder="John Doe", key="signup_name")
        email = st.text_input("Email address", placeholder="you@example.com", key="signup_email")
        password = st.text_input("Password (min 6 characters)", type="password", key="signup_pass")
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm")

        st.markdown("** I am a...**")
        # st.radio lets the user pick one option
        # The value returned is the selected label string
        role_label = st.radio(
            label="Account type",
            options=["Job Seeker", "Employer"],
            horizontal=True,
            label_visibility="collapsed",  # Hide the label text
            key="signup_role"
        )
        # map the display label to the database value
        role = "seeker" if role_label == "Job Seeker" else "employer"

        if st.button("Create account", use_container_width=True, type="primary"):
            if password != confirm:
                st.error("Password do not Match!!.")
            else:
                success, message = do_signup(full_name, email, password, role)
                if success:
                    st.success(message)
                    st.balloons()
                    # send them to the login page after successful signup
                    st.session_state["auth_page"] = "login"
                    st.rerun()
                else:
                    st.error(message)

        st.divider()
        st.markdown("Already have an account?")
        if st.button("Back to Login", use_container_width=True):
            st.session_state["auth_page"] = "login"
            st.rerun()


# Sidebar (shown only after logged in)
def show_sidebar():
    """
    Displays the navigation sidebar for logged-in users.
    The sidebar content differs based on role.
    """
    with st.sidebar:
        st.markdown(f"### Hello {st.session_state['user_name']}")
        st.markdown(
            f"`{'Job Seeker' if st.session_state['role'] == 'seeker' else 'Employer'}`"
        )
        st.divider()

        if st.session_state["role"] == "seeker":
            st.markdown("**Navigation**")
            if st.button("My Dashboard", use_container_width=True):
                st.session_state["current_page"] = "seeker_dashboard"
                st.session_state.pop("show_preferences", None)
                st.rerun()
            if st.button("Browse Jobs", use_container_width=True):
                st.session_state["current_page"] = "job_board"
                st.session_state.pop("show_preferences", None)
                st.rerun()
            if st.button("Job Preferences", use_container_width=True):
                # Always accessible — goes straight to the preference screen
                # regardless of what page the user is currently on
                st.session_state["show_preferences"] = True
                st.session_state["current_page"] = "home"
                st.rerun()

        else:  # employer
            st.markdown("**Navigation**")
            if st.button("Dashboard", use_container_width=True):
                st.session_state["current_page"] = "employer_dashboard"
                st.rerun()

        st.divider()
        if st.button("Log out", use_container_width=True):
            do_logout()


def show_preference_prompt():
    """
    Shown to seekers on first login OR when they click 'Update Preferences'
    Lets them select job categories and keywords so the job board
    only shows relevant jobs
    """
    prefs = get_seeker_preferences(st.session_state["user_id"])

    # Job categories the seeker can pick from
    ALL_CATEGORIES = [
        "Technology & Software",
        "Data Science & AI",
        "Cybersecurity",
        "Networking & Infrastructure",
        "Human Resources",
        "Finance & Accounting",
        "Marketing & Sales",
        "Operations & Management",
        "Design & Creative",
        "Healthcare",
        "Legal",
        "Other"
    ]

    st.markdown("### Set Your Job Preferences")
    st.markdown(
        "Select the types of jobs you are interested in."
        "Your job board will only show matching listings"
    )

    selected_cats = st.multiselect(
        "Job Categories (select all that apply)",
        options=ALL_CATEGORIES,
        default=prefs["categories"] if prefs["categories"] else [],
        key="pref_categories"
    )

    keywords = st.text_input(
        "Specific Skills or keywords (optional)",
        value=", ".join(prefs["keywords"]),
        placeholder="e.g. python, machine learning, remote",
        key="pref_keywords",
        help="Comma-separated. Jobs containing these words will be prioritised."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Preferences", type="primary",
                     use_container_width=True):
            if not selected_cats:
                st.warning("Please select at least one category.")
            else:
                kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
                save_seeker_preferences(
                    seeker_id=st.session_state["user_id"],
                    categories=", ".join(selected_cats),
                    keywords=", ".join(kw_list)
                )
                st.session_state["show_preferences"] = False
                st.session_state["current_page"] = "seeker_dashboard"
                st.success("Preferences saved!")
                st.rerun()

    with col2:
        if st.button("Skip for now", use_container_width=True):
            st.session_state["show_preferences"] = False
            st.session_state["current_page"] = "seeker_dashboard"
            st.rerun()


# MAIN ROUTER
# ─────────────────────────────────────────────
# This is where everything comes together.
# Streamlit runs this section every time the page loads.
#
# FLOW:
#   Not logged in → show login or signup form
#   Logged in as seeker → show seeker welcome + sidebar
#   Logged in as employer → show employer welcome + sidebar

def main():
    if not st.session_state["logged_in"]:
        # User is not logged in - show auth forms
        if st.session_state["auth_page"] == "signup":
            show_signup_page()
        else:
            show_login_page()

    else:
        # User is Logged in - Shows sidebar and Welcome Screen
        show_sidebar()

        page = st.session_state.get("current_page", "home")
        role = st.session_state["role"]
        name = st.session_state["user_name"]

        if page == "home":
            if role == "seeker":
                prefs = get_seeker_preferences(st.session_state["user_id"])
                if not prefs["categories"] or st.session_state.get("show_preferences"):
                    show_preference_prompt()
                else:
                    st.title(f"Welcome Back, {name}!")
                    st.markdown("Use the **sidebar** to navigate.")
                    st.markdown(
                        "You can update your job preferences at any time "
                        "using the **Job Preferences** button in the sidebar."
                    )
            elif role == "employer":
                st.title(f"Welcome Back, {name}!")
                st.markdown(
                    "Use the **sidebar** to manage your job listings and review applicants."
                )
        elif page == "seeker_dashboard":
            show_seeker_dashboard()

        elif page == "job_board":
            show_seeker_dashboard()  # Tab 3 of the same dashboard

        elif page == "employer_dashboard":
            show_employer_dashboard()

        elif page == "apply":
            show_apply_page()


# Entry Point
# Python runs this when the file is executed directly
# When Streamlit runs this file, __name__ == "__main__" is True.
if __name__ == "__main__":
    main()