import sqlite3
from dataclasses import dataclass
from datetime import datetime

STATUS_OPTIONS = (
    ("all", "All statuses"),
    ("pending", "Pending"),
    ("shortlisted", "Shortlisted"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
)

SORT_OPTIONS = (
    ("newest", "Newest first"),
    ("oldest", "Oldest first"),
    ("job-title", "Job title A–Z"),
    ("company", "Company A–Z"),
    ("status", "Status A–Z"),
)

STATUS_VALUES = {value: label for value, label in STATUS_OPTIONS if value != "all"}

SORT_EXPRESSIONS = {
    "newest": "applications.applied_at DESC, applications.application_id DESC",
    "oldest": "applications.applied_at ASC, applications.application_id ASC",
    "job-title": ("jobs.title COLLATE NOCASE ASC, applications.applied_at DESC"),
    "company": (
        "employers.company_name COLLATE NOCASE ASC, " "applications.applied_at DESC"
    ),
    "status": ("applications.status COLLATE NOCASE ASC, applications.applied_at DESC"),
}


@dataclass(frozen=True)
class ApplicationHistoryOptions:
    status_key: str
    status_value: str | None
    sort_key: str

    @property
    def filters_active(self) -> bool:
        return self.status_key != "all" or self.sort_key != "newest"


def parse_application_history_options(
    status_value: str | None,
    sort_value: str | None,
) -> ApplicationHistoryOptions:
    """Normalize untrusted query parameters to supported history options."""

    status_key = (status_value or "all").strip().lower()
    sort_key = (sort_value or "newest").strip().lower()

    if status_key not in {"all", *STATUS_VALUES}:
        status_key = "all"

    if sort_key not in SORT_EXPRESSIONS:
        sort_key = "newest"

    return ApplicationHistoryOptions(
        status_key=status_key,
        status_value=STATUS_VALUES.get(status_key),
        sort_key=sort_key,
    )


def get_application_history(
    connection: sqlite3.Connection,
    seeker_id: int,
    options: ApplicationHistoryOptions,
) -> tuple[list[dict], int]:
    """Return one seeker's application history and their unfiltered total."""

    total_row = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM applications
        WHERE seeker_id = ?
        """,
        (seeker_id,),
    ).fetchone()
    total_count = int(total_row["total"] if total_row else 0)

    query = """
        SELECT
            applications.application_id,
            applications.status AS application_status,
            applications.applied_at,
            jobs.job_id,
            jobs.title,
            jobs.location,
            jobs.employment_type,
            employers.company_name
        FROM applications
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN employers
            ON employers.employer_id = jobs.employer_id
        WHERE applications.seeker_id = ?
    """
    parameters: list[object] = [seeker_id]

    if options.status_value:
        query += " AND applications.status = ?"
        parameters.append(options.status_value)

    query += f" ORDER BY {SORT_EXPRESSIONS[options.sort_key]}"
    rows = connection.execute(query, parameters).fetchall()
    applications = []

    for row in rows:
        application = dict(row)
        application["application_date"] = format_application_date(
            application.get("applied_at")
        )
        applications.append(application)

    return applications, total_count


def format_application_date(value: object) -> str:
    """Format SQLite timestamps for display while handling legacy values."""

    if value is None:
        return "Date unavailable"

    if isinstance(value, datetime):
        parsed_value = value
    else:
        text_value = str(value).strip()

        if not text_value:
            return "Date unavailable"

        try:
            parsed_value = datetime.fromisoformat(text_value)
        except ValueError:
            return text_value

    return parsed_value.strftime("%d %b %Y")
