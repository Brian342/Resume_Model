from datetime import datetime, timedelta
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "Resume_app.db")


# Connection Helper
def get_connection():
    """
    Opens and creates a connection to the sqlite Database.
    check_same_thread = False is required because streamlit runs
    on multiple threads and streamlit would otherwise create more Errors
    detect_types allows us to store and retrieve Python datetime objects
    directly instead of converting them manually.
    """
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )

    #
    #
    conn.row_factory = sqlite3.Row

    return conn


# Table definitions
def create_table():
    """
    Creates all tables if they do not already exist.
    This runs every time the app starts. It is safe to call repeatedly
    because of the IF NOT EXIST Clause.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # user Table-----------------------------------
    # Stores both job seekers and employers in one table
    # The 'Role' column tells us which type of user they are.
    # Passwords are stored as hashed strings (never plain text)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT        NOT NULL,
    email           TEXT        NOT NULL UNIQUE,
    password        TEXT        NOT NULL,
    role            TEXT        NOT NULL CHECK(role IN ('seeker', 'employer')),
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # JOBS' TABLE
    # jobs are posted by employers (linked via employer_id -> user.id),
    # is_active lets employers hide a job without deleting it.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs(
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id         INTEGER NOT NULL REFERENCES    users(id),
    title               TEXT        NOT NULL,
    company             TEXT        NOT NULL,
    location            TEXT        NOT NULL,
    description         TEXT        NOT NULL,
    requirements        TEXT        NOT NULL,
    salary              TEXT,
    is_active           INTEGER    DEFAULT 1,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Application table
    # Created when a seeker applies to a job
    # Resume_path: where we saved the uploaded pdf on disk
    # answers: JSON string of the seeker's screener questions answers
    # ai_score: 0-100 score f
    # ml_label: Classification from your ML model e.g. "Qualified" / "Not Qualified"
    # Status: employer's decision - pending/ approved / rejected
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id),
    seeker_id       INTEGER NOT NULL REFERENCES users(id),
    resume_path     TEXT,
    answers         TEXT,
    ai_score        REAL        DEFAULT NULL,
    ml_label        TEXT        DEFAULT NULL,
    status          TEXT        DEFAULT 'pending'
                            CHECK(status IN ('pending', 'approved', 'rejected')),
    applied_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, seeker_id)
    )  
    """)

    conn.commit()
    conn.close()
    print("Tables Created (or already exist).")

    # User Function


def create_user(full_name, email, password_hash, role):
    """
    Inserts a new user into the database.

    Note: password_hash should already before calling this.
    Hashed passwords are in Sample File.py using bcrypt before passing here.
    Returns True if successful, False if email already exists.
    """
    conn = get_connection()
    try:
        conn.execute("""
        INSERT INTO users (full_name, email, password, role)
        VALUES (?,?,?,?)
        """, (full_name, email, password_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Unique constraint on email was violated - email already registered
        return False
    finally:
        conn.close()


def get_user_by_email(email):
    """
    Fetches a single user row by email address.
    used during login to verify credentials.

    Returns a Row object (like a dict) or None if not found.
    Access fields like: user["email"], user["role], user["id"]
    """
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    """Fetches a user by their ID. Used to display profile info."""
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return user


# Job Functions

def create_job(employer_id, title, company, location, description, requirements, salary=""):
    """
    Inserts a new job posting into the database.
    called from the employer dashboard when they post a new job.

    Returns the ID of the newly created job
    """
    conn = get_connection()
    cursor = conn.execute("""
    INSERT INTO jobs (employer_id, title, company, location, description, requirements,
    salary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (employer_id, title, company, location, description, requirements, salary))
    conn.commit()
    job_id = cursor.lastrowid  # The auto-assigned ID of the new row
    conn.close()
    return job_id


def get_all_active_jobs():
    """
    Fetches all active job listings for the job seeker's job board.
    Joins with users' table to get employer's name.

    Returns a list of Row objects.
    """
    conn = get_connection()
    jobs = conn.execute("""
        SELECT j.*, u.full_name AS employer_name
        FROM jobs j
        JOIN users u ON j.employer_id = u.id
        WHERE j.is_active = 1
        ORDER BY j.created_at DESC
    """).fetchall()
    conn.close()
    return jobs


def get_jobs_by_employer(employer_id):
    """
    Fetches all jobs posted by a specific employer.
    Used on the employer dashboard to show their listings.
    """
    conn = get_connection()
    jobs = conn.execute("""
        SELECT * FROM jobs
        WHERE employer_id = ?
        ORDER BY created_at DESC
    """, (employer_id,)).fetchall()
    conn.close()
    return jobs


def get_job_by_id(job_id):
    """
    Fetch a single job by ID.
    Used on the job detail page to show full information
    """
    conn = get_connection()
    job = conn.execute(
        "SELECT * FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    conn.close()
    return job


def toggle_job_active(job_id, is_active):
    """
    Activate or deactivates a job listing.
    Employers can pause a listing without deleting it.
    is_active: 1 = visible to seekers, 0 = hidden
    """
    conn = get_connection()
    conn.execute(
        "UPDATE jobs SET is_active = ? WHERE id = ?", (is_active, job_id)
    )
    conn.commit()
    conn.close()


# Application Functions
def create_application(job_id, seeker_id, resume_path, answers_json):
    """
    Saves a job application to the database.

    answers_json: a JSON string of the seeker's question answers.
    we use json.dumps() in apply.py before passing it here, e.g.:

        import JSON
        answer_json = json.dumps({"q1": "answer1", "q2": "answer2"})
    Returns True if saved, False if already applied to this job
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO applications (job_id, seeker_id, resume_path, answers)
            VALUES (?, ?, ?, ?)
        """, (job_id, seeker_id, resume_path, answers_json))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # UNIQUE(job_id, seeker_id) violated - already applied
        return False
    finally:
        conn.close()


def get_applications_by_seeker(seeker_id):
    """
    Fetches all applications made by a job seeker.
    Used on the seeker dashboard to show "My Applications" tab.
    Joins jobs table to show job title and company
    """
    conn = get_connection()
    apps = conn.execute("""
    SELECT a.*, j.title AS job_title, j.company, j.location
    FROM applications a
    JOIN jobs j ON a.job_id = j.id
    WHERE a.seeker_id = ?
    ORDER BY a.applied_at DESC
    """, (seeker_id,)).fetchall()
    conn.close()
    return apps


def get_applications_by_job(job_id):
    """
    Fetches all applications for a specific job.
    Used on the employer dashboard to review applicants
    Joins users table to show seeker name and email
    """
    conn = get_connection()
    apps = conn.execute("""
        SELECT a.*, u.full_name AS seeker_name, u.email AS seeker_email
        FROM applications a
        JOIN users u ON a.seeker_id = u.id
        WHERE a.job_id = ?
        ORDER BY CASE WHEN a.ai_score IS NULL THEN 1 ELSE 0 END,
                 a.ai_score DESC
    """, (job_id,)).fetchall()
    conn.close()
    return apps


def get_seeker_stats(seeker_id):
    """
    Returns a dictionary of dynamic stats for the seeker dashboard.
    These power the st.metric() cards at the top of the dashboard

    Returns:
        {
            "total_applied": 5,
            "qualified": 2, # applications where status = 'approved'
            "pending": 2,
            "rejected":1
        }
    """
    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE seeker_id = ?", (seeker_id,)
    ).fetchone()[0]

    qualified = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE seeker_id = ? AND status = 'approved'",
        (seeker_id,)
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE seeker_id = ? AND status = 'pending'",
        (seeker_id,)
    ).fetchone()[0]

    rejected = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE seeker_id = ? AND status = 'rejected'",
        (seeker_id,)
    ).fetchone()[0]

    conn.close()

    return {
        "total_applied": total,
        "qualified": qualified,
        "pending": pending,
        "rejected": rejected
    }


def update_application_status(application_id, status):
    """
    Updates the AI score and Ml label for an application after screening.
    Called from apply.py after your AI/ML model processes the resume.

    ai_score: float 0-100
    ml_label: string e.g "Qualified", "Not Qualified", "Review Needed"
    """

    conn = get_connection()
    conn.execute("""
        UPDATE applications
        SET  status = ?
        WHERE id = ?
    """, (status, application_id))
    conn.commit()
    conn.close()


def update_application_score(application_id, ai_score, ml_label):
    """
        Updates the AI score and ML label after resume screening.
        Called from apply.py after the ML model processes the resume.

        ai_score: float 0-100
        ml_label: string e.g "Qualified", "Not Qualified", "Review Needed"
        """
    conn = get_connection()
    conn.execute("""
            UPDATE applications
            SET ai_score = ?, ml_label = ?
            WHERE id = ?
        """, (ai_score, ml_label, application_id))
    conn.commit()
    conn.close()


def has_applied(job_id, seeker_id):
    """
    Checks if a seeker has already applied to a specific job.
    Used in the job detail page to show 'Already Applied' Instead of Apply button.

    Returns True or False
    """
    conn = get_connection()
    result = conn.execute(
        "SELECT id FROM applications WHERE job_id = ? AND seeker_id = ?",
        (job_id, seeker_id)
    ).fetchone()
    conn.close()
    return result is not None


def delete_job(job_id: int):
    """
    Permanently deletes a job and All its applications
    Called from employer_dashboard when employer confirms deletion.

    We delete applications first because of the REFERENCES constraint
    SQLITE won't let you delete a job that has applications pointing to it.
    """
    conn = get_connection()
    conn.execute("DELETE FROM applications WHERE job_id =?", (job_id,))
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def update_job(job_id: int, title: str, company: str, location: str,
               description: str, requirements: str, salary: str):
    """
    Updates an existing job posting with new values.
    Called from employer_dashboard when employer saves edits
    """
    conn = get_connection()
    conn.execute("""
    UPDATE jobs
        SET title=?, company=?, location=?,
            description=?, requirements=?, salary=?
        WHERE id=?
    """, (title, company, location, description, requirements, salary, job_id))
    conn.commit()
    conn.close()


# Initialise On Import
create_table()
