import sqlite3
from dataclasses import dataclass

WITHDRAWABLE_STATUS = "Pending"
WITHDRAWN_STATUS = "Withdrawn"


@dataclass(frozen=True)
class WithdrawalResult:
    outcome: str
    previous_status: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome == "withdrawn"


def can_employer_update_application(status: object) -> bool:
    """Withdrawn applications are final and cannot be reviewed by employers."""

    return str(status or "").strip() != WITHDRAWN_STATUS


def withdraw_application(
    connection: sqlite3.Connection,
    application_id: int,
    seeker_id: int,
) -> WithdrawalResult:
    """Atomically withdraw one seeker-owned application while it is Pending."""

    cursor = connection.execute(
        """
        UPDATE applications
        SET status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
          AND seeker_id = ?
          AND status = ?
        """,
        (
            WITHDRAWN_STATUS,
            application_id,
            seeker_id,
            WITHDRAWABLE_STATUS,
        ),
    )

    if cursor.rowcount == 1:
        connection.commit()
        return WithdrawalResult(outcome="withdrawn")

    application = connection.execute(
        """
        SELECT status
        FROM applications
        WHERE application_id = ? AND seeker_id = ?
        """,
        (application_id, seeker_id),
    ).fetchone()

    if application is None:
        return WithdrawalResult(outcome="not_found")

    return WithdrawalResult(
        outcome="not_pending",
        previous_status=str(application["status"] or ""),
    )
