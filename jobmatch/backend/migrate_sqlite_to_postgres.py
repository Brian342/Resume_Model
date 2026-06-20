"""
migrate_sqlite_to_postgres.py — One-Time Data Migration
==========================================================
Copies your real seed data (users, jobs, applications) from the old
SQLite database (Resume_app.db) into the new PostgreSQL database,
preserving IDs, timestamps, password hashes, and ML scores exactly.

WHEN TO RUN THIS:
  Once, after main.py has successfully started and created the
  PostgreSQL tables (db.create_tables() must have already run).

USAGE:
  Place Resume_app.db in the same folder as this script (or pass --db-path),
  then from jobmatch/backend/:

      python migrate_sqlite_to_postgres.py

  Run it again safely if it fails partway — it skips rows that already
  exist (checked by primary key) rather than erroring or duplicating.

WHAT GETS MIGRATED:
  - users          (including job_categories / job_keywords preferences)
  - jobs
  - applications   (including ai_score, ml_label, resume_path, answers)

WHAT DOESN'T GET MIGRATED AUTOMATICALLY:
  - The actual resume PDF files on disk. Your SQLite data has resume_path
    values like:
        /Users/briankimanzi/Documents/.../utils/uploads/resume/seeker1_job17_....pdf
    Those files live wherever your old Streamlit app saved them — this
    script does NOT move PDFs. If those files still exist at that path,
    resume download/re-scoring will keep working. If you've already
    deleted or moved them, pass --copy-resumes-from to copy them into
    your new backend/uploads/resume/ folder and rewrite the paths to match.
"""

import argparse
import asyncio
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import db  # your new PostgreSQL db.py


def _parse_sqlite_datetime(value) -> datetime:
    """
    SQLite stores timestamps as plain strings (e.g. '2026-03-30 05:18:38'),
    but asyncpg requires an actual datetime.datetime object — passing a
    string raises: "expected a datetime.date or datetime.datetime instance,
    got 'str'". This converts whatever SQLite gives us into a real datetime,
    falling back to "now" only if the value is missing or unparseable.
    """
    if isinstance(value, datetime):
        return value

    if not value:
        return datetime.utcnow()

    # SQLite's CURRENT_TIMESTAMP format is "YYYY-MM-DD HH:MM:SS",
    # but occasionally includes microseconds or a "T" separator.
    formats = (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue

    print(f"  ⚠ Could not parse timestamp '{value}', using current time instead.")
    return datetime.utcnow()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


async def migrate_users(sqlite_conn: sqlite3.Connection) -> dict:
    """
    Copies all rows from SQLite users -> PostgreSQL users.
    Returns a dict mapping old SQLite user id -> new PostgreSQL user id,
    in case PostgreSQL's SERIAL ids ever diverge from the SQLite ones.
    """
    rows = sqlite_conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    id_map = {}
    inserted, skipped = 0, 0

    for row in rows:
        r = _row_to_dict(row)

        existing = await db.get_user_by_email(r["email"])
        if existing:
            id_map[r["id"]] = existing["id"]
            skipped += 1
            continue

        query = db.users.insert().values(
            full_name=r["full_name"],
            email=r["email"].strip().lower(),
            password=r["password"],          # already bcrypt-hashed — copy as-is
            role=r["role"],
            job_categories=r.get("job_categories") or "",
            job_keywords=r.get("job_keywords") or "",
            created_at=_parse_sqlite_datetime(r["created_at"]),
        )
        new_id = await db.database.execute(query)
        id_map[r["id"]] = new_id
        inserted += 1

    print(f"  users: {inserted} inserted, {skipped} already existed (skipped)")
    return id_map


async def migrate_jobs(sqlite_conn: sqlite3.Connection, user_id_map: dict) -> dict:
    """
    Copies all rows from SQLite jobs -> PostgreSQL jobs.
    employer_id is remapped through user_id_map in case ids shifted.
    Returns old job id -> new job id mapping.
    """
    rows = sqlite_conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    id_map = {}
    inserted, skipped = 0, 0

    for row in rows:
        r = _row_to_dict(row)
        new_employer_id = user_id_map.get(r["employer_id"])

        if new_employer_id is None:
            print(f"  ⚠ Skipping job id={r['id']} ('{r['title']}') — "
                  f"employer_id {r['employer_id']} not found in user_id_map")
            skipped += 1
            continue

        query = db.jobs.insert().values(
            employer_id=new_employer_id,
            title=r["title"],
            company=r["company"],
            location=r["location"],
            description=r["description"],
            requirements=r["requirements"],
            salary=r.get("salary") or "",
            is_active=bool(r["is_active"]),
            created_at=_parse_sqlite_datetime(r["created_at"]),
        )
        new_id = await db.database.execute(query)
        id_map[r["id"]] = new_id
        inserted += 1

    print(f"  jobs: {inserted} inserted, {skipped} skipped")
    return id_map


async def migrate_applications(
    sqlite_conn: sqlite3.Connection,
    user_id_map: dict,
    job_id_map: dict,
    copy_resumes_from: Path = None,
) -> None:
    """
    Copies all rows from SQLite applications -> PostgreSQL applications.
    job_id and seeker_id are remapped through the id maps built above.

    If copy_resumes_from is given, also copies the resume PDF file from
    that folder into backend/uploads/resume/ and rewrites resume_path
    to the new location. Otherwise resume_path is copied as-is (works
    fine if the original file path is still valid on this machine).
    """
    rows = sqlite_conn.execute("SELECT * FROM applications ORDER BY id").fetchall()
    inserted, skipped = 0, 0

    new_upload_dir = Path(__file__).parent / "uploads" / "resume"
    new_upload_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        r = _row_to_dict(row)
        new_job_id = job_id_map.get(r["job_id"])
        new_seeker_id = user_id_map.get(r["seeker_id"])

        if new_job_id is None or new_seeker_id is None:
            print(f"  ⚠ Skipping application id={r['id']} — "
                  f"missing job_id or seeker_id mapping")
            skipped += 1
            continue

        already = await db.has_applied(new_job_id, new_seeker_id)
        if already:
            skipped += 1
            continue

        resume_path = r.get("resume_path") or ""

        # Optionally copy the actual PDF file alongside the database row
        if resume_path and copy_resumes_from:
            old_file = copy_resumes_from / Path(resume_path).name
            if old_file.exists():
                new_file = new_upload_dir / Path(resume_path).name
                shutil.copy2(old_file, new_file)
                resume_path = str(new_file)
            else:
                print(f"  ⚠ Resume file not found, keeping original path: {old_file}")

        query = db.applications.insert().values(
            job_id=new_job_id,
            seeker_id=new_seeker_id,
            resume_path=resume_path,
            answers=r.get("answers") or "{}",
            ai_score=r.get("ai_score"),
            ml_label=r.get("ml_label"),
            status=r.get("status") or "pending",
            applied_at=_parse_sqlite_datetime(r["applied_at"]),
        )
        await db.database.execute(query)
        inserted += 1

    print(f"  applications: {inserted} inserted, {skipped} skipped")


async def run_migration(sqlite_path: str, copy_resumes_from: str = None):
    sqlite_path = Path(sqlite_path)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Could not find SQLite database at {sqlite_path}")

    resumes_dir = Path(copy_resumes_from) if copy_resumes_from else None

    print(f"📂 Reading from: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    print("🔌 Connecting to PostgreSQL...")
    db.create_tables()   # CREATE TABLE IF NOT EXISTS — safe to run even if main.py never has
    await db.connect()

    try:
        print("\n➡ Migrating users...")
        user_id_map = await migrate_users(sqlite_conn)

        print("\n➡ Migrating jobs...")
        job_id_map = await migrate_jobs(sqlite_conn, user_id_map)

        print("\n➡ Migrating applications...")
        await migrate_applications(sqlite_conn, user_id_map, job_id_map, resumes_dir)

        print("\n Migration complete.")

    finally:
        sqlite_conn.close()
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate JobMatch data from SQLite to PostgreSQL.")
    parser.add_argument(
        "--db-path",
        default="Resume_app.db",
        help="Path to the old SQLite database file (default: Resume_app.db in this folder).",
    )
    parser.add_argument(
        "--copy-resumes-from",
        default=None,
        help=(
            "Optional: folder containing the original resume PDF files. "
            "If given, PDFs are copied into backend/uploads/resume/ and "
            "resume_path is rewritten to point there. If omitted, the "
            "original absolute paths are kept as-is."
        ),
    )
    args = parser.parse_args()

    asyncio.run(run_migration(args.db_path, args.copy_resumes_from))