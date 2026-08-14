import sqlite3
from dataclasses import dataclass
from datetime import datetime

AVAILABLE_JOB_STATUS = "Open"


@dataclass(frozen=True)
class SavedJobResult:
    outcome: str

    @property
    def succeeded(self) -> bool:
        return self.outcome in {"saved", "removed"}


def toggle_saved_job(
    connection: sqlite3.Connection,
    seeker_id: int,
    job_id: int,
) -> SavedJobResult:
    """Save an open job or remove an existing seeker-owned saved job."""

    saved_job = connection.execute(
        """
        SELECT saved_job_id
        FROM saved_jobs
        WHERE seeker_id = ? AND job_id = ?
        """,
        (seeker_id, job_id),
    ).fetchone()

    if saved_job is not None:
        connection.execute(
            """
            DELETE FROM saved_jobs
            WHERE seeker_id = ? AND job_id = ?
            """,
            (seeker_id, job_id),
        )
        connection.commit()
        return SavedJobResult(outcome="removed")

    job = connection.execute(
        """
        SELECT status
        FROM jobs
        WHERE job_id = ?
        """,
        (job_id,),
    ).fetchone()

    if job is None:
        return SavedJobResult(outcome="not_found")

    if str(job["status"] or "") != AVAILABLE_JOB_STATUS:
        return SavedJobResult(outcome="unavailable")

    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO saved_jobs (seeker_id, job_id)
        VALUES (?, ?)
        """,
        (seeker_id, job_id),
    )
    connection.commit()

    if cursor.rowcount == 1:
        return SavedJobResult(outcome="saved")

    return SavedJobResult(outcome="already_saved")


def get_saved_jobs(
    connection: sqlite3.Connection,
    seeker_id: int,
) -> list[dict]:
    """Return only one seeker's saved jobs, newest saved item first."""

    rows = connection.execute(
        """
        SELECT
            saved_jobs.saved_job_id,
            saved_jobs.saved_at,
            jobs.job_id,
            jobs.title,
            jobs.description,
            jobs.location,
            jobs.employment_type,
            jobs.salary_min,
            jobs.salary_max,
            jobs.category,
            jobs.experience_level,
            jobs.work_mode,
            jobs.status,
            employers.company_name
        FROM saved_jobs
        JOIN jobs
            ON jobs.job_id = saved_jobs.job_id
        JOIN employers
            ON employers.employer_id = jobs.employer_id
        WHERE saved_jobs.seeker_id = ?
        ORDER BY saved_jobs.saved_at DESC, saved_jobs.saved_job_id DESC
        """,
        (seeker_id,),
    ).fetchall()

    saved_jobs = []

    for row in rows:
        saved_job = dict(row)
        saved_job["is_available"] = saved_job["status"] == AVAILABLE_JOB_STATUS
        saved_job["saved_date"] = format_saved_date(saved_job.get("saved_at"))
        saved_jobs.append(saved_job)

    return saved_jobs


def format_saved_date(value: object) -> str:
    """Format a SQLite timestamp for the Saved Jobs page."""

    if value is None:
        return "Date unavailable"

    text_value = str(value).strip()

    if not text_value:
        return "Date unavailable"

    try:
        parsed_value = datetime.fromisoformat(text_value)
    except ValueError:
        return text_value

    return parsed_value.strftime("%d %b %Y")
