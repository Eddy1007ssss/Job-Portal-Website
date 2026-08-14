import sqlite3
from dataclasses import dataclass
from datetime import datetime

PROFILE_VISIBILITY_OPTIONS = ("Employers", "Private")


@dataclass(frozen=True)
class PortalResult:
    outcome: str
    record_id: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome in {"created", "updated", "deleted"}


def get_companies(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute("""
        SELECT
            company_profiles.profile_id,
            company_profiles.employer_id,
            company_profiles.company_name,
            company_profiles.industry,
            company_profiles.address,
            company_profiles.company_description,
            company_profiles.company_size,
            company_profiles.logo_url,
            COUNT(
                CASE WHEN jobs.status = 'Open' THEN jobs.job_id END
            ) AS active_job_count
        FROM company_profiles
        LEFT JOIN jobs
            ON jobs.employer_id = company_profiles.employer_id
        GROUP BY company_profiles.profile_id
        ORDER BY
            active_job_count DESC,
            company_profiles.company_name COLLATE NOCASE ASC
        """).fetchall()

    return [dict(row) for row in rows]


def get_portal_stats(connection: sqlite3.Connection) -> dict[str, int]:
    queries = {
        "company_count": "SELECT COUNT(*) FROM company_profiles",
        "open_job_count": "SELECT COUNT(*) FROM jobs WHERE status = 'Open'",
        "seeker_count": "SELECT COUNT(*) FROM seekers",
    }

    return {
        name: int(connection.execute(query).fetchone()[0])
        for name, query in queries.items()
    }


def create_job_notifications_for_job(
    connection: sqlite3.Connection,
    job_id: int,
) -> int:
    """Create one new-job notification for every registered seeker."""

    job = connection.execute(
        "SELECT status FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()

    if job is None or job["status"] != "Open":
        return 0

    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO job_notifications (seeker_id, job_id)
        SELECT seeker_id, ?
        FROM seekers
        """,
        (job_id,),
    )
    connection.commit()
    return max(cursor.rowcount, 0)


def sync_recent_job_notifications(
    connection: sqlite3.Connection,
    seeker_id: int,
) -> int:
    """Backfill notifications for recent open jobs after this feature is added."""

    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO job_notifications (seeker_id, job_id)
        SELECT ?, recent_jobs.job_id
        FROM (
            SELECT job_id
            FROM jobs
            WHERE status = 'Open'
            ORDER BY created_at DESC, job_id DESC
            LIMIT 50
        ) AS recent_jobs
        """,
        (seeker_id,),
    )
    connection.commit()
    return max(cursor.rowcount, 0)


def get_job_notifications(
    connection: sqlite3.Connection,
    seeker_id: int,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
            job_notifications.notification_id,
            job_notifications.is_read,
            job_notifications.created_at AS notification_created_at,
            jobs.job_id,
            jobs.title,
            jobs.location,
            jobs.employment_type,
            jobs.work_mode,
            jobs.status,
            employers.company_name
        FROM job_notifications
        JOIN jobs
            ON jobs.job_id = job_notifications.job_id
        JOIN employers
            ON employers.employer_id = jobs.employer_id
        WHERE job_notifications.seeker_id = ?
        ORDER BY
            job_notifications.is_read ASC,
            job_notifications.created_at DESC,
            job_notifications.notification_id DESC
        """,
        (seeker_id,),
    ).fetchall()
    notifications = []

    for row in rows:
        notification = dict(row)
        notification["message"] = (
            f"{notification['company_name']} posted a new job: "
            f"{notification['title']}"
        )
        notification["display_date"] = _format_date(
            notification.get("notification_created_at")
        )
        notifications.append(notification)

    return notifications


def get_unread_notification_count(
    connection: sqlite3.Connection,
    seeker_id: int,
) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM job_notifications
        WHERE seeker_id = ? AND is_read = 0
        """,
        (seeker_id,),
    ).fetchone()
    return int(row[0] if row else 0)


def mark_notification_read(
    connection: sqlite3.Connection,
    seeker_id: int,
    notification_id: int,
) -> PortalResult:
    cursor = connection.execute(
        """
        UPDATE job_notifications
        SET is_read = 1
        WHERE notification_id = ? AND seeker_id = ?
        """,
        (notification_id, seeker_id),
    )

    if cursor.rowcount != 1:
        return PortalResult(outcome="not_found")

    connection.commit()
    return PortalResult(outcome="updated", record_id=notification_id)


def mark_all_notifications_read(
    connection: sqlite3.Connection,
    seeker_id: int,
) -> int:
    cursor = connection.execute(
        """
        UPDATE job_notifications
        SET is_read = 1
        WHERE seeker_id = ? AND is_read = 0
        """,
        (seeker_id,),
    )
    connection.commit()
    return max(cursor.rowcount, 0)


def get_notification_job_id(
    connection: sqlite3.Connection,
    seeker_id: int,
    notification_id: int,
) -> int | None:
    row = connection.execute(
        """
        SELECT job_id
        FROM job_notifications
        WHERE notification_id = ? AND seeker_id = ?
        """,
        (notification_id, seeker_id),
    ).fetchone()

    if row is None:
        return None

    return int(row["job_id"])


def get_seeker_settings(
    connection: sqlite3.Connection,
    seeker_id: int,
) -> dict:
    row = connection.execute(
        """
        SELECT
            seekers.full_name,
            seekers.email,
            seekers.contact_number,
            seeker_settings.email_notifications,
            seeker_settings.application_updates,
            seeker_settings.job_recommendations,
            seeker_settings.profile_visibility
        FROM seekers
        LEFT JOIN seeker_settings
            ON seeker_settings.seeker_id = seekers.seeker_id
        WHERE seekers.seeker_id = ?
        """,
        (seeker_id,),
    ).fetchone()

    if row is None:
        return {}

    settings = dict(row)
    settings["email_notifications"] = _setting_value(settings["email_notifications"])
    settings["application_updates"] = _setting_value(settings["application_updates"])
    settings["job_recommendations"] = _setting_value(settings["job_recommendations"])
    settings["profile_visibility"] = settings["profile_visibility"] or "Employers"
    return settings


def update_seeker_settings(
    connection: sqlite3.Connection,
    seeker_id: int,
    email_notifications: bool,
    application_updates: bool,
    job_recommendations: bool,
    profile_visibility: str,
) -> PortalResult:
    if profile_visibility not in PROFILE_VISIBILITY_OPTIONS:
        return PortalResult(outcome="invalid")

    connection.execute(
        """
        INSERT INTO seeker_settings (
            seeker_id,
            email_notifications,
            application_updates,
            job_recommendations,
            profile_visibility,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(seeker_id) DO UPDATE SET
            email_notifications = excluded.email_notifications,
            application_updates = excluded.application_updates,
            job_recommendations = excluded.job_recommendations,
            profile_visibility = excluded.profile_visibility,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            seeker_id,
            int(email_notifications),
            int(application_updates),
            int(job_recommendations),
            profile_visibility,
        ),
    )
    connection.commit()
    return PortalResult(outcome="updated", record_id=seeker_id)


def _format_date(value: object) -> str:
    if value is None:
        return "Just now"

    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)

    return parsed.strftime("%d %b %Y · %I:%M %p")


def _setting_value(value: object) -> bool:
    if value is None:
        return True

    return bool(value)
