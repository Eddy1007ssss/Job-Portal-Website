import sqlite3
from dataclasses import dataclass

REAPPLYABLE_STATUS = "Withdrawn"


@dataclass(frozen=True)
class ApplicationSubmissionResult:
    outcome: str
    application_id: int | None = None
    previous_status: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome in {"submitted", "reapplied"}


def can_submit_application(existing_status: object) -> bool:
    """Allow a first application or a retry after the seeker withdrew it."""

    if existing_status is None:
        return True

    return str(existing_status).strip() == REAPPLYABLE_STATUS


def submit_application(
    connection: sqlite3.Connection,
    seeker_id: int,
    job_id: int,
    cover_letter: str,
    resume_filename: str | None,
) -> ApplicationSubmissionResult:
    """Create an application or reactivate its withdrawn record."""

    existing_application = connection.execute(
        """
        SELECT application_id, status
        FROM applications
        WHERE seeker_id = ? AND job_id = ?
        """,
        (seeker_id, job_id),
    ).fetchone()

    if existing_application is not None:
        previous_status = str(existing_application["status"] or "").strip()

        if not can_submit_application(previous_status):
            return ApplicationSubmissionResult(
                outcome="already_exists",
                application_id=int(existing_application["application_id"]),
                previous_status=previous_status,
            )

        cursor = connection.execute(
            """
            UPDATE applications
            SET cover_letter = ?,
                resume_filename = ?,
                status = 'Pending',
                applied_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE application_id = ?
              AND seeker_id = ?
              AND status = ?
            """,
            (
                cover_letter,
                resume_filename,
                existing_application["application_id"],
                seeker_id,
                REAPPLYABLE_STATUS,
            ),
        )

        if cursor.rowcount == 1:
            connection.commit()
            return ApplicationSubmissionResult(
                outcome="reapplied",
                application_id=int(existing_application["application_id"]),
                previous_status=previous_status,
            )

        connection.rollback()
        return ApplicationSubmissionResult(
            outcome="already_exists",
            application_id=int(existing_application["application_id"]),
            previous_status=previous_status,
        )

    try:
        cursor = connection.execute(
            """
            INSERT INTO applications (
                seeker_id,
                job_id,
                cover_letter,
                resume_filename,
                status
            )
            VALUES (?, ?, ?, ?, 'Pending')
            """,
            (
                seeker_id,
                job_id,
                cover_letter,
                resume_filename,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        return ApplicationSubmissionResult(outcome="already_exists")

    if cursor.lastrowid is None:
        raise RuntimeError("Failed to create the application record.")

    return ApplicationSubmissionResult(
        outcome="submitted",
        application_id=int(cursor.lastrowid),
    )
