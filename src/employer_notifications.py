import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

NOTIFICATION_FILTERS = (
    "all",
    "unread",
    "applications",
    "interviews",
)
MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


def sync_employer_notifications(
    connection: sqlite3.Connection,
    employer_id: int,
) -> int:
    """Create missing notifications from employer-owned activity."""

    before_changes = connection.total_changes

    connection.execute(
        """
        INSERT OR IGNORE INTO employer_notifications (
            employer_id,
            event_key,
            notification_type,
            application_id,
            title,
            message,
            created_at
        )
        SELECT
            jobs.employer_id,
            'application:' || applications.application_id || ':' ||
                COALESCE(applications.applied_at, ''),
            'new_application',
            applications.application_id,
            'New application received',
            seekers.full_name || ' applied for ' || jobs.title || '.',
            COALESCE(applications.applied_at, CURRENT_TIMESTAMP)
        FROM applications
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id
        WHERE jobs.employer_id = ?
        """,
        (employer_id,),
    )

    connection.execute(
        """
        INSERT OR IGNORE INTO employer_notifications (
            employer_id,
            event_key,
            notification_type,
            application_id,
            title,
            message,
            created_at
        )
        SELECT
            jobs.employer_id,
            'withdrawal:' || applications.application_id || ':' ||
                COALESCE(applications.updated_at, ''),
            'application_withdrawn',
            applications.application_id,
            'Application withdrawn',
            seekers.full_name || ' withdrew the application for ' ||
                jobs.title || '.',
            COALESCE(applications.updated_at, CURRENT_TIMESTAMP)
        FROM applications
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id
        WHERE jobs.employer_id = ?
          AND applications.status = 'Withdrawn'
        """,
        (employer_id,),
    )

    connection.execute(
        """
        INSERT OR IGNORE INTO employer_notifications (
            employer_id,
            event_key,
            notification_type,
            application_id,
            interview_id,
            title,
            message,
            created_at
        )
        SELECT
            interviews.employer_id,
            'interview-response:' || interviews.interview_id || ':' ||
                interviews.status || ':' ||
                COALESCE(interviews.seeker_response_at, ''),
            CASE interviews.status
                WHEN 'Accepted' THEN 'interview_accepted'
                ELSE 'interview_declined'
            END,
            applications.application_id,
            interviews.interview_id,
            CASE interviews.status
                WHEN 'Accepted' THEN 'Interview invitation accepted'
                ELSE 'Interview invitation declined'
            END,
            seekers.full_name ||
                CASE interviews.status
                    WHEN 'Accepted' THEN ' accepted the interview for '
                    ELSE ' declined the interview for '
                END || jobs.title || '.',
            interviews.seeker_response_at
        FROM interviews
        JOIN applications
            ON applications.application_id = interviews.application_id
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id
        WHERE interviews.employer_id = ?
          AND interviews.status IN ('Accepted', 'Declined')
          AND interviews.seeker_response_at IS NOT NULL
        """,
        (employer_id,),
    )

    connection.commit()
    return connection.total_changes - before_changes


def sync_employer_activity_for_application(
    connection: sqlite3.Connection,
    application_id: int,
) -> int:
    row = connection.execute(
        """
        SELECT jobs.employer_id
        FROM applications
        JOIN jobs
            ON jobs.job_id = applications.job_id
        WHERE applications.application_id = ?
        """,
        (application_id,),
    ).fetchone()

    if row is None:
        return 0

    return sync_employer_notifications(
        connection,
        int(row["employer_id"]),
    )


def sync_employer_activity_for_interview(
    connection: sqlite3.Connection,
    interview_id: int,
) -> int:
    row = connection.execute(
        """
        SELECT employer_id
        FROM interviews
        WHERE interview_id = ?
        """,
        (interview_id,),
    ).fetchone()

    if row is None:
        return 0

    return sync_employer_notifications(
        connection,
        int(row["employer_id"]),
    )


def get_employer_notifications(
    connection: sqlite3.Connection,
    employer_id: int,
    filter_key: str = "all",
    *,
    now: datetime | None = None,
) -> list[dict]:
    selected_filter = normalise_notification_filter(filter_key)
    query = """
        SELECT
            employer_notifications.*,
            applications.job_id,
            jobs.title AS job_title,
            seekers.full_name AS applicant_name
        FROM employer_notifications
        LEFT JOIN applications
            ON applications.application_id =
               employer_notifications.application_id
        LEFT JOIN jobs
            ON jobs.job_id = applications.job_id
        LEFT JOIN seekers
            ON seekers.seeker_id = applications.seeker_id
        WHERE employer_notifications.employer_id = ?
    """
    parameters: list[object] = [employer_id]

    if selected_filter == "unread":
        query += " AND employer_notifications.is_read = 0"
    elif selected_filter == "applications":
        query += (
            " AND employer_notifications.notification_type "
            "IN ('new_application', 'application_withdrawn')"
        )
    elif selected_filter == "interviews":
        query += (
            " AND employer_notifications.notification_type "
            "IN ('interview_accepted', 'interview_declined')"
        )

    query += """
        ORDER BY
            employer_notifications.is_read ASC,
            employer_notifications.created_at DESC,
            employer_notifications.notification_id DESC
    """
    rows = connection.execute(query, parameters).fetchall()
    return [_decorate_notification(dict(row), now=now) for row in rows]


def get_employer_notification_summary(
    connection: sqlite3.Connection,
    employer_id: int,
) -> dict[str, int]:
    row = connection.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) AS unread,
            SUM(
                CASE
                    WHEN notification_type IN (
                        'new_application',
                        'application_withdrawn'
                    ) THEN 1
                    ELSE 0
                END
            ) AS applications,
            SUM(
                CASE
                    WHEN notification_type IN (
                        'interview_accepted',
                        'interview_declined'
                    ) THEN 1
                    ELSE 0
                END
            ) AS interviews
        FROM employer_notifications
        WHERE employer_id = ?
        """,
        (employer_id,),
    ).fetchone()
    return {
        "total": int(row["total"] or 0) if row else 0,
        "unread": int(row["unread"] or 0) if row else 0,
        "applications": int(row["applications"] or 0) if row else 0,
        "interviews": int(row["interviews"] or 0) if row else 0,
    }


def get_unread_employer_notification_count(
    connection: sqlite3.Connection,
    employer_id: int,
) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM employer_notifications
        WHERE employer_id = ? AND is_read = 0
        """,
        (employer_id,),
    ).fetchone()
    return int(row["total"] if row else 0)


def mark_employer_notification_read(
    connection: sqlite3.Connection,
    employer_id: int,
    notification_id: int,
) -> bool:
    cursor = connection.execute(
        """
        UPDATE employer_notifications
        SET is_read = 1
        WHERE notification_id = ? AND employer_id = ?
        """,
        (notification_id, employer_id),
    )
    connection.commit()
    return cursor.rowcount == 1


def mark_all_employer_notifications_read(
    connection: sqlite3.Connection,
    employer_id: int,
) -> int:
    cursor = connection.execute(
        """
        UPDATE employer_notifications
        SET is_read = 1
        WHERE employer_id = ? AND is_read = 0
        """,
        (employer_id,),
    )
    connection.commit()
    return int(cursor.rowcount)


def get_employer_notification_target(
    connection: sqlite3.Connection,
    employer_id: int,
    notification_id: int,
) -> dict | None:
    row = connection.execute(
        """
        SELECT
            notification_id,
            notification_type,
            application_id,
            interview_id
        FROM employer_notifications
        WHERE notification_id = ? AND employer_id = ?
        """,
        (notification_id, employer_id),
    ).fetchone()
    return dict(row) if row else None


def normalise_notification_filter(filter_key: str | None) -> str:
    cleaned_filter = str(filter_key or "all").strip().lower()
    return cleaned_filter if cleaned_filter in NOTIFICATION_FILTERS else "all"


def _decorate_notification(
    notification: dict,
    *,
    now: datetime | None = None,
) -> dict:
    created_at = _parse_database_time(notification.get("created_at"))
    current_time = _normalise_time(now)

    if created_at is None:
        notification["display_time"] = "Time unavailable"
        notification["relative_time"] = ""
        return notification

    local_time = created_at.astimezone(MALAYSIA_TIMEZONE)
    notification["display_time"] = local_time.strftime(
        "%d %b %Y, %I:%M %p",
    )
    notification["relative_time"] = _relative_time(created_at, current_time)
    return notification


def _parse_database_time(value: object) -> datetime | None:
    if value is None:
        return None

    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _normalise_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _relative_time(created_at: datetime, now: datetime) -> str:
    seconds = max(0, int((now - created_at).total_seconds()))

    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} hr ago"
    if seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"

    return created_at.astimezone(MALAYSIA_TIMEZONE).strftime("%d %b %Y")
