import re
import sqlite3
from dataclasses import dataclass
from datetime import date

SKILL_NAME_MAX_LENGTH = 80
CERTIFICATE_NAME_MAX_LENGTH = 120
CERTIFICATE_ISSUER_MAX_LENGTH = 120
MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True)
class CertificateDetails:
    name: str
    issuer: str
    issue_date: str


@dataclass(frozen=True)
class CredentialResult:
    outcome: str
    record_id: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome in {"added", "updated"}


def normalize_profile_text(value: str) -> str:
    """Trim input and collapse repeated whitespace before saving it."""

    return " ".join(value.split())


def validate_skill_name(name: str) -> str | None:
    normalized_name = normalize_profile_text(name)

    if not normalized_name:
        return "Skill name is required."

    if len(normalized_name) > SKILL_NAME_MAX_LENGTH:
        return f"Skill name must not exceed {SKILL_NAME_MAX_LENGTH} characters."

    return None


def validate_certificate_details(
    details: CertificateDetails,
    current_month: str,
) -> str | None:
    name = normalize_profile_text(details.name)
    issuer = normalize_profile_text(details.issuer)

    if not name:
        return "Certificate name is required."

    if len(name) > CERTIFICATE_NAME_MAX_LENGTH:
        return (
            "Certificate name must not exceed "
            f"{CERTIFICATE_NAME_MAX_LENGTH} characters."
        )

    if len(issuer) > CERTIFICATE_ISSUER_MAX_LENGTH:
        return "Issuer must not exceed " f"{CERTIFICATE_ISSUER_MAX_LENGTH} characters."

    if not details.issue_date:
        return None

    issue_month = _parse_month(details.issue_date)
    current_month_value = _parse_month(current_month)

    if issue_month is None:
        return "Certificate issue date must be a valid month."

    if current_month_value is None:
        raise ValueError("current_month must use YYYY-MM format")

    if issue_month > current_month_value:
        return "Certificate issue date cannot be in the future."

    return None


def add_skill_record(
    connection: sqlite3.Connection,
    seeker_id: int,
    name: str,
) -> CredentialResult:
    normalized_name = normalize_profile_text(name)

    if validate_skill_name(normalized_name):
        return CredentialResult(outcome="invalid")

    duplicate = connection.execute(
        """
        SELECT skill_id
        FROM seeker_skills
        WHERE seeker_id = ?
          AND skill_name = ? COLLATE NOCASE
        """,
        (seeker_id, normalized_name),
    ).fetchone()

    if duplicate is not None:
        return CredentialResult(outcome="duplicate")

    try:
        cursor = connection.execute(
            """
            INSERT INTO seeker_skills (seeker_id, skill_name)
            VALUES (?, ?)
            """,
            (seeker_id, normalized_name),
        )
    except sqlite3.IntegrityError:
        return CredentialResult(outcome="duplicate")

    connection.commit()
    return CredentialResult(outcome="added", record_id=cursor.lastrowid)


def update_skill_record(
    connection: sqlite3.Connection,
    seeker_id: int,
    skill_id: int,
    name: str,
) -> CredentialResult:
    normalized_name = normalize_profile_text(name)

    if validate_skill_name(normalized_name):
        return CredentialResult(outcome="invalid")

    existing = connection.execute(
        """
        SELECT skill_id
        FROM seeker_skills
        WHERE skill_id = ? AND seeker_id = ?
        """,
        (skill_id, seeker_id),
    ).fetchone()

    if existing is None:
        return CredentialResult(outcome="not_found")

    duplicate = connection.execute(
        """
        SELECT skill_id
        FROM seeker_skills
        WHERE seeker_id = ?
          AND skill_id != ?
          AND skill_name = ? COLLATE NOCASE
        """,
        (seeker_id, skill_id, normalized_name),
    ).fetchone()

    if duplicate is not None:
        return CredentialResult(outcome="duplicate")

    connection.execute(
        """
        UPDATE seeker_skills
        SET skill_name = ?
        WHERE skill_id = ? AND seeker_id = ?
        """,
        (normalized_name, skill_id, seeker_id),
    )
    connection.commit()
    return CredentialResult(outcome="updated", record_id=skill_id)


def get_certificate_record(
    connection: sqlite3.Connection,
    seeker_id: int,
    certificate_id: int,
):
    return connection.execute(
        """
        SELECT *
        FROM seeker_certificates
        WHERE certificate_id = ? AND seeker_id = ?
        """,
        (certificate_id, seeker_id),
    ).fetchone()


def add_certificate_record(
    connection: sqlite3.Connection,
    seeker_id: int,
    details: CertificateDetails,
    stored_filename: str | None = None,
    original_filename: str | None = None,
) -> CredentialResult:
    cursor = connection.execute(
        """
        INSERT INTO seeker_certificates (
            seeker_id,
            certificate_name,
            issuer,
            issue_date,
            certificate_filename,
            original_filename
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            seeker_id,
            normalize_profile_text(details.name),
            normalize_profile_text(details.issuer),
            details.issue_date,
            stored_filename,
            original_filename,
        ),
    )
    connection.commit()
    return CredentialResult(outcome="added", record_id=cursor.lastrowid)


def update_certificate_record(
    connection: sqlite3.Connection,
    seeker_id: int,
    certificate_id: int,
    details: CertificateDetails,
    stored_filename: str | None,
    original_filename: str | None,
) -> CredentialResult:
    cursor = connection.execute(
        """
        UPDATE seeker_certificates
        SET certificate_name = ?,
            issuer = ?,
            issue_date = ?,
            certificate_filename = ?,
            original_filename = ?
        WHERE certificate_id = ? AND seeker_id = ?
        """,
        (
            normalize_profile_text(details.name),
            normalize_profile_text(details.issuer),
            details.issue_date,
            stored_filename,
            original_filename,
            certificate_id,
            seeker_id,
        ),
    )

    if cursor.rowcount != 1:
        return CredentialResult(outcome="not_found")

    connection.commit()
    return CredentialResult(outcome="updated", record_id=certificate_id)


def _parse_month(value: str) -> date | None:
    match = MONTH_PATTERN.fullmatch(value)

    if match is None:
        return None

    try:
        return date(int(match.group(1)), int(match.group(2)), 1)
    except ValueError:
        return None
