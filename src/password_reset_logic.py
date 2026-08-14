import hashlib
import re
import secrets
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PASSWORD_RESET_LIFETIME_MINUTES = 30
ACCOUNT_TABLES = {
    "seeker": {
        "table": "seekers",
        "id_column": "seeker_id",
        "email_column": "email",
        "login_endpoint": "seeker.login",
    },
    "employer": {
        "table": "employers",
        "id_column": "employer_id",
        "email_column": "company_email",
        "login_endpoint": "employer.login",
    },
}


@dataclass(frozen=True)
class PasswordResetResult:
    outcome: str
    message: str = ""
    account_type: str | None = None
    account_id: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome == "updated"


def validate_email_address(email: str) -> str | None:
    if not EMAIL_PATTERN.fullmatch(email.strip()):
        return "Please enter a valid registered email address."

    return None


def validate_new_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must contain at least 8 characters."

    if not any(character.isupper() for character in password):
        return "Password must include at least one uppercase letter."

    if not any(character.islower() for character in password):
        return "Password must include at least one lowercase letter."

    if not any(character.isdigit() for character in password):
        return "Password must include at least one number."

    return None


def create_password_reset_token(
    connection: sqlite3.Connection,
    email: str,
    account_type: str,
    *,
    now: datetime | None = None,
) -> str | None:
    """Create a one-time token without revealing whether an account exists."""

    account = ACCOUNT_TABLES.get(account_type)

    if account is None:
        return None

    normalized_email = email.strip().lower()
    row = connection.execute(
        f"""
        SELECT {account['id_column']} AS account_id
        FROM {account['table']}
        WHERE LOWER({account['email_column']}) = ?
        """,
        (normalized_email,),
    ).fetchone()

    if row is None:
        return None

    current_time = _normalise_time(now)
    account_id = int(row["account_id"])

    connection.execute(
        """
        UPDATE password_reset_tokens
        SET used_at = ?
        WHERE account_type = ?
          AND account_id = ?
          AND used_at IS NULL
        """,
        (
            _database_time(current_time),
            account_type,
            account_id,
        ),
    )

    raw_token = secrets.token_urlsafe(32)
    expires_at = current_time + timedelta(minutes=PASSWORD_RESET_LIFETIME_MINUTES)
    connection.execute(
        """
        INSERT INTO password_reset_tokens (
            account_type,
            account_id,
            token_hash,
            expires_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            account_type,
            account_id,
            _hash_token(raw_token),
            _database_time(expires_at),
        ),
    )
    connection.commit()
    return raw_token


def get_password_reset_token_status(
    connection: sqlite3.Connection,
    token: str,
    *,
    now: datetime | None = None,
) -> PasswordResetResult:
    if not token:
        return PasswordResetResult(
            outcome="invalid",
            message="This password reset link is invalid.",
        )

    row = connection.execute(
        """
        SELECT
            reset_id,
            account_type,
            account_id,
            expires_at,
            used_at
        FROM password_reset_tokens
        WHERE token_hash = ?
        """,
        (_hash_token(token),),
    ).fetchone()

    if row is None or row["used_at"] is not None:
        return PasswordResetResult(
            outcome="invalid",
            message="This password reset link is invalid or has already been used.",
        )

    current_time = _normalise_time(now)
    expires_at = _parse_database_time(row["expires_at"])

    if expires_at is None or expires_at <= current_time:
        return PasswordResetResult(
            outcome="expired",
            message="This password reset link has expired. Request a new link.",
            account_type=row["account_type"],
            account_id=int(row["account_id"]),
        )

    return PasswordResetResult(
        outcome="valid",
        account_type=row["account_type"],
        account_id=int(row["account_id"]),
    )


def reset_account_password(
    connection: sqlite3.Connection,
    token: str,
    new_password: str,
    confirm_password: str,
    *,
    now: datetime | None = None,
    check_hash: Callable[[str, str], bool] | None = None,
    generate_hash: Callable[[str], str] | None = None,
) -> PasswordResetResult:
    token_status = get_password_reset_token_status(
        connection,
        token,
        now=now,
    )

    if token_status.outcome != "valid":
        return token_status

    if new_password != confirm_password:
        return PasswordResetResult(
            outcome="mismatch",
            message="Passwords do not match.",
            account_type=token_status.account_type,
            account_id=token_status.account_id,
        )

    password_error = validate_new_password(new_password)

    if password_error:
        return PasswordResetResult(
            outcome="weak",
            message=password_error,
            account_type=token_status.account_type,
            account_id=token_status.account_id,
        )

    if token_status.account_type is None or token_status.account_id is None:
        return PasswordResetResult(
            outcome="invalid",
            message="This password reset link is invalid.",
        )

    if check_hash is None or generate_hash is None:
        from werkzeug.security import (
            check_password_hash,
            generate_password_hash,
        )

        check_hash = check_password_hash
        generate_hash = generate_password_hash

    account = ACCOUNT_TABLES[token_status.account_type]
    current_password = connection.execute(
        f"""
        SELECT password_hash
        FROM {account['table']}
        WHERE {account['id_column']} = ?
        """,
        (token_status.account_id,),
    ).fetchone()

    if current_password is None:
        return PasswordResetResult(
            outcome="invalid",
            message="The account for this reset link no longer exists.",
        )

    if check_hash(current_password["password_hash"], new_password):
        return PasswordResetResult(
            outcome="same_password",
            message="Choose a password different from your current password.",
            account_type=token_status.account_type,
            account_id=token_status.account_id,
        )

    token_hash = _hash_token(token)
    connection.execute(
        f"""
        UPDATE {account['table']}
        SET password_hash = ?
        WHERE {account['id_column']} = ?
        """,
        (
            generate_hash(new_password),
            token_status.account_id,
        ),
    )
    connection.execute(
        """
        UPDATE password_reset_tokens
        SET used_at = ?
        WHERE token_hash = ? AND used_at IS NULL
        """,
        (
            _database_time(_normalise_time(now)),
            token_hash,
        ),
    )
    connection.commit()

    return PasswordResetResult(
        outcome="updated",
        message="Your password has been reset successfully.",
        account_type=token_status.account_type,
        account_id=token_status.account_id,
    )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
