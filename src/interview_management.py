import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

INTERVIEW_MODES = ("Online", "In-person", "Phone")
INTERVIEW_STATUSES = (
    "Pending",
    "Accepted",
    "Declined",
    "Cancelled",
    "Completed",
)
RESPONSES = ("Accepted", "Declined")
MIN_REASON_LENGTH = 5
MAX_REASON_LENGTH = 500
MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


@dataclass(frozen=True)
class InterviewDetails:
    scheduled_date: str
    scheduled_time: str
    duration_minutes: str
    interview_mode: str
    location_or_link: str
    notes: str = ""


@dataclass(frozen=True)
class InterviewResult:
    outcome: str
    message: str = ""
    record_id: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome in {
            "created",
            "rescheduled",
            "accepted",
            "declined",
            "cancelled",
            "completed",
        }


def validate_interview_details(
    details: InterviewDetails,
    *,
    now: datetime | None = None,
) -> str | None:
    scheduled_at = _parse_form_datetime(
        details.scheduled_date,
        details.scheduled_time,
    )

    if scheduled_at is None:
        return "Select a valid interview date and time."

    current_time = _normalise_time(now)

    if scheduled_at <= current_time:
        return "The interview must be scheduled in the future."

    if scheduled_at > current_time + timedelta(days=365):
        return "The interview cannot be scheduled more than one year ahead."

    try:
        duration_minutes = int(details.duration_minutes)
    except TypeError, ValueError:
        return "Select a valid interview duration."

    if duration_minutes < 15 or duration_minutes > 240:
        return "Interview duration must be between 15 and 240 minutes."

    if details.interview_mode not in INTERVIEW_MODES:
        return "Select a valid interview mode."

    location_or_link = details.location_or_link.strip()

    if len(location_or_link) < 3:
        if details.interview_mode == "Online":
            return "Enter the online meeting link."

        if details.interview_mode == "Phone":
            return "Enter the phone number or call instructions."

        return "Enter the interview location."

    if len(location_or_link) > 500:
        return "The interview location or meeting link is too long."

    if details.interview_mode == "Online" and not _is_safe_web_url(location_or_link):
        return "Online interviews require a valid http or https meeting link."

    if len(details.notes.strip()) > 1000:
        return "Interview notes must not exceed 1000 characters."

    return None


def save_interview(
    connection: sqlite3.Connection,
    employer_id: int,
    application_id: int,
    details: InterviewDetails,
    *,
    now: datetime | None = None,
) -> InterviewResult:
    application = _get_owned_application(
        connection,
        employer_id,
        application_id,
    )

    if application is None:
        return InterviewResult(
            outcome="not_found",
            message="The selected application was not found.",
        )

    if str(application["application_status"] or "") != "Shortlisted":
        return InterviewResult(
            outcome="not_shortlisted",
            message="Shortlist the applicant before scheduling an interview.",
        )

    validation_error = validate_interview_details(details, now=now)

    if validation_error:
        return InterviewResult(
            outcome="invalid",
            message=validation_error,
        )

    scheduled_at = _parse_form_datetime(
        details.scheduled_date,
        details.scheduled_time,
    )

    if scheduled_at is None:
        return InterviewResult(
            outcome="invalid",
            message="Select a valid interview date and time.",
        )

    existing = connection.execute(
        """
        SELECT interview_id
        FROM interviews
        WHERE application_id = ?
        """,
        (application_id,),
    ).fetchone()
    parameters = (
        _database_time(scheduled_at),
        int(details.duration_minutes),
        details.interview_mode,
        details.location_or_link.strip(),
        details.notes.strip() or None,
    )

    if existing is None:
        cursor = connection.execute(
            """
            INSERT INTO interviews (
                application_id,
                employer_id,
                scheduled_at,
                duration_minutes,
                interview_mode,
                location_or_link,
                notes,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
            """,
            (
                application_id,
                employer_id,
                *parameters,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to create the interview record.")

        interview_id = int(cursor.lastrowid)
        outcome = "created"
        message = "Interview invitation scheduled successfully."
    else:
        interview_id = int(existing["interview_id"])
        connection.execute(
            """
            UPDATE interviews
            SET
                scheduled_at = ?,
                duration_minutes = ?,
                interview_mode = ?,
                location_or_link = ?,
                notes = ?,
                status = 'Pending',
                seeker_response_at = NULL,
                seeker_response_reason = NULL,
                cancellation_reason = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE interview_id = ?
              AND employer_id = ?
            """,
            (
                *parameters,
                interview_id,
                employer_id,
            ),
        )
        outcome = "rescheduled"
        message = "Interview rescheduled. The applicant must respond again."

    connection.commit()
    return InterviewResult(
        outcome=outcome,
        message=message,
        record_id=interview_id,
    )


def respond_to_interview(
    connection: sqlite3.Connection,
    seeker_id: int,
    interview_id: int,
    response: str,
    reason: str = "",
    *,
    now: datetime | None = None,
) -> InterviewResult:
    if response not in RESPONSES:
        return InterviewResult(
            outcome="invalid_response",
            message="Select a valid interview response.",
        )

    response_reason = str(reason or "").strip()

    if response == "Declined":
        reason_error = validate_interview_reason(
            response_reason,
            action_name="declining the interview",
        )

        if reason_error:
            return InterviewResult(
                outcome="invalid_reason",
                message=reason_error,
            )
    else:
        response_reason = ""

    current_time = _normalise_time(now)
    cursor = connection.execute(
        """
        UPDATE interviews
        SET
            status = ?,
            seeker_response_at = ?,
            seeker_response_reason = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE interview_id = ?
          AND status = 'Pending'
          AND scheduled_at > ?
          AND application_id IN (
              SELECT application_id
              FROM applications
              WHERE seeker_id = ?
          )
        """,
        (
            response,
            _database_time(current_time),
            response_reason or None,
            interview_id,
            _database_time(current_time),
            seeker_id,
        ),
    )

    if cursor.rowcount == 1:
        connection.commit()
        return InterviewResult(
            outcome=response.lower(),
            message=f"Interview invitation {response.lower()}.",
            record_id=interview_id,
        )

    row = connection.execute(
        """
        SELECT interviews.status, interviews.scheduled_at
        FROM interviews
        JOIN applications
            ON applications.application_id = interviews.application_id
        WHERE interviews.interview_id = ?
          AND applications.seeker_id = ?
        """,
        (interview_id, seeker_id),
    ).fetchone()

    if row is None:
        return InterviewResult(
            outcome="not_found",
            message="The selected interview was not found.",
        )

    if str(row["status"]) != "Pending":
        return InterviewResult(
            outcome="already_responded",
            message="This interview invitation has already been updated.",
        )

    return InterviewResult(
        outcome="past",
        message="This interview time has already passed.",
    )


def cancel_interview(
    connection: sqlite3.Connection,
    employer_id: int,
    interview_id: int,
    reason: str,
) -> InterviewResult:
    cancellation_reason = str(reason or "").strip()
    reason_error = validate_interview_reason(
        cancellation_reason,
        action_name="cancelling the interview",
    )

    if reason_error:
        return InterviewResult(
            outcome="invalid_reason",
            message=reason_error,
        )

    cursor = connection.execute(
        """
        UPDATE interviews
        SET
            status = 'Cancelled',
            cancellation_reason = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE interview_id = ?
          AND employer_id = ?
          AND status IN ('Pending', 'Accepted')
        """,
        (cancellation_reason, interview_id, employer_id),
    )

    if cursor.rowcount == 1:
        connection.commit()
        return InterviewResult(
            outcome="cancelled",
            message="Interview cancelled successfully.",
            record_id=interview_id,
        )

    return _interview_action_failure(
        connection,
        employer_id,
        interview_id,
        "This interview cannot be cancelled in its current status.",
    )


def validate_interview_reason(
    reason: str,
    *,
    action_name: str,
) -> str | None:
    cleaned_reason = str(reason or "").strip()

    if len(cleaned_reason) < MIN_REASON_LENGTH:
        return (
            f"Please provide at least {MIN_REASON_LENGTH} characters before "
            f"{action_name}."
        )

    if len(cleaned_reason) > MAX_REASON_LENGTH:
        return f"The reason cannot exceed {MAX_REASON_LENGTH} characters."

    return None


def complete_interview(
    connection: sqlite3.Connection,
    employer_id: int,
    interview_id: int,
    *,
    now: datetime | None = None,
) -> InterviewResult:
    current_time = _normalise_time(now)
    cursor = connection.execute(
        """
        UPDATE interviews
        SET
            status = 'Completed',
            updated_at = CURRENT_TIMESTAMP
        WHERE interview_id = ?
          AND employer_id = ?
          AND status = 'Accepted'
          AND scheduled_at <= ?
        """,
        (
            interview_id,
            employer_id,
            _database_time(current_time),
        ),
    )

    if cursor.rowcount == 1:
        connection.commit()
        return InterviewResult(
            outcome="completed",
            message="Interview marked as completed.",
            record_id=interview_id,
        )

    return _interview_action_failure(
        connection,
        employer_id,
        interview_id,
        "Only an accepted interview that has started can be completed.",
    )


def get_seeker_interviews(
    connection: sqlite3.Connection,
    seeker_id: int,
    *,
    now: datetime | None = None,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
            interviews.*,
            applications.seeker_id,
            jobs.job_id,
            jobs.title AS job_title,
            jobs.location AS job_location,
            employers.company_name
        FROM interviews
        JOIN applications
            ON applications.application_id = interviews.application_id
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN employers
            ON employers.employer_id = jobs.employer_id
        WHERE applications.seeker_id = ?
        ORDER BY
            CASE interviews.status
                WHEN 'Pending' THEN 0
                WHEN 'Accepted' THEN 1
                ELSE 2
            END,
            interviews.scheduled_at ASC,
            interviews.interview_id DESC
        """,
        (seeker_id,),
    ).fetchall()
    return [_decorate_interview(dict(row), now=now) for row in rows]


def get_employer_interviews(
    connection: sqlite3.Connection,
    employer_id: int,
    status: str | None = None,
    *,
    now: datetime | None = None,
) -> list[dict]:
    query = """
        SELECT
            interviews.*,
            applications.seeker_id,
            applications.status AS application_status,
            jobs.job_id,
            jobs.title AS job_title,
            seekers.full_name AS applicant_name,
            seekers.email AS applicant_email
        FROM interviews
        JOIN applications
            ON applications.application_id = interviews.application_id
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id
        WHERE interviews.employer_id = ?
    """
    parameters: list[object] = [employer_id]

    if status in INTERVIEW_STATUSES:
        query += " AND interviews.status = ?"
        parameters.append(status)

    query += " ORDER BY interviews.scheduled_at ASC, interviews.interview_id DESC"
    rows = connection.execute(query, parameters).fetchall()
    return [_decorate_interview(dict(row), now=now) for row in rows]


def get_interview_application(
    connection: sqlite3.Connection,
    employer_id: int,
    application_id: int,
    *,
    now: datetime | None = None,
) -> tuple[dict | None, dict | None]:
    application_row = _get_owned_application(
        connection,
        employer_id,
        application_id,
    )

    if application_row is None:
        return None, None

    interview_row = connection.execute(
        """
        SELECT *
        FROM interviews
        WHERE application_id = ? AND employer_id = ?
        """,
        (application_id, employer_id),
    ).fetchone()
    interview = (
        _decorate_interview(dict(interview_row), now=now) if interview_row else None
    )
    return dict(application_row), interview


def get_pending_interview_count(
    connection: sqlite3.Connection,
    seeker_id: int,
    *,
    now: datetime | None = None,
) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM interviews
        JOIN applications
            ON applications.application_id = interviews.application_id
        WHERE applications.seeker_id = ?
          AND interviews.status = 'Pending'
          AND interviews.scheduled_at > ?
        """,
        (seeker_id, _database_time(_normalise_time(now))),
    ).fetchone()
    return int(row["total"] if row else 0)


def _get_owned_application(
    connection: sqlite3.Connection,
    employer_id: int,
    application_id: int,
):
    return connection.execute(
        """
        SELECT
            applications.application_id,
            applications.seeker_id,
            applications.status AS application_status,
            applications.applied_at,
            jobs.job_id,
            jobs.title AS job_title,
            jobs.location AS job_location,
            seekers.full_name AS applicant_name,
            seekers.email AS applicant_email,
            employers.company_name
        FROM applications
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id
        JOIN employers
            ON employers.employer_id = jobs.employer_id
        WHERE applications.application_id = ?
          AND jobs.employer_id = ?
        """,
        (application_id, employer_id),
    ).fetchone()


def _decorate_interview(
    interview: dict,
    *,
    now: datetime | None = None,
) -> dict:
    scheduled_at = _parse_database_time(interview.get("scheduled_at"))
    current_time = _normalise_time(now)

    if scheduled_at is None:
        interview["display_date"] = "Date unavailable"
        interview["display_time"] = "Time unavailable"
        interview["scheduled_input"] = ""
        interview["is_upcoming"] = False
    else:
        local_time = scheduled_at.astimezone(MALAYSIA_TIMEZONE)
        interview["display_date"] = local_time.strftime("%a, %d %b %Y")
        interview["display_time"] = local_time.strftime("%I:%M %p")
        interview["scheduled_input"] = local_time.strftime("%Y-%m-%dT%H:%M")
        interview["is_upcoming"] = scheduled_at > current_time

    interview["can_respond"] = (
        interview.get("status") == "Pending" and interview["is_upcoming"]
    )
    location_or_link = str(interview.get("location_or_link") or "")
    interview["join_url"] = (
        location_or_link
        if interview.get("interview_mode") == "Online"
        and _is_safe_web_url(location_or_link)
        else None
    )
    return interview


def _interview_action_failure(
    connection: sqlite3.Connection,
    employer_id: int,
    interview_id: int,
    invalid_status_message: str,
) -> InterviewResult:
    row = connection.execute(
        """
        SELECT interview_id
        FROM interviews
        WHERE interview_id = ? AND employer_id = ?
        """,
        (interview_id, employer_id),
    ).fetchone()

    if row is None:
        return InterviewResult(
            outcome="not_found",
            message="The selected interview was not found.",
        )

    return InterviewResult(
        outcome="invalid_status",
        message=invalid_status_message,
    )


def _parse_form_datetime(date_value: str, time_value: str) -> datetime | None:
    try:
        parsed = datetime.strptime(
            f"{date_value.strip()} {time_value.strip()}",
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=MALAYSIA_TIMEZONE)
    except AttributeError, ValueError:
        return None

    return parsed.astimezone(timezone.utc)


def _normalise_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _database_time(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(
            sep=" ",
            timespec="seconds",
        )
    )


def _parse_database_time(value: object) -> datetime | None:
    if value is None:
        return None

    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None

    return _normalise_time(parsed)


def _is_safe_web_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
