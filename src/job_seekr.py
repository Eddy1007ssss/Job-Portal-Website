"""Job seeker registration routes and validation."""

from __future__ import annotations

import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash

from .database import get_db

bp = Blueprint("job_seeker", __name__)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9]{8,15}$")


@dataclass(frozen=True)
class RegistrationData:
    full_name: str
    email: str
    phone_number: str
    password: str
    confirm_password: str


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _normalize_phone(phone_number: str) -> str:
    prefix = "+" if phone_number.strip().startswith("+") else ""
    digits = "".join(character for character in phone_number if character.isdigit())
    return f"{prefix}{digits}"


def _registration_data(source: dict) -> RegistrationData:
    return RegistrationData(
        full_name=str(source.get("full_name", "")).strip(),
        email=str(source.get("email", "")).strip().lower(),
        phone_number=_normalize_phone(str(source.get("phone_number", ""))),
        password=str(source.get("password", "")),
        confirm_password=str(source.get("confirm_password", "")),
    )


def _validate(data: RegistrationData) -> dict[str, str]:
    errors: dict[str, str] = {}

    if len(data.full_name) < 2:
        errors["full_name"] = "Enter your full name using at least 2 characters."
    elif len(data.full_name) > 100:
        errors["full_name"] = "Full name must not exceed 100 characters."

    if not EMAIL_PATTERN.fullmatch(data.email):
        errors["email"] = "Enter a valid email address."

    if not PHONE_PATTERN.fullmatch(data.phone_number):
        errors["phone_number"] = "Enter a phone number containing 8 to 15 digits."

    if len(data.password) < 8:
        errors["password"] = "Password must contain at least 8 characters."
    elif not re.search(r"[A-Z]", data.password):
        errors["password"] = "Password must include an uppercase letter."
    elif not re.search(r"[a-z]", data.password):
        errors["password"] = "Password must include a lowercase letter."
    elif not re.search(r"[0-9]", data.password):
        errors["password"] = "Password must include a number."

    if data.confirm_password != data.password:
        errors["confirm_password"] = "The passwords do not match."

    return errors


def _create_job_seeker(data: RegistrationData) -> int:
    database = get_db()
    cursor = database.execute(
        """
        INSERT INTO job_seekers (full_name, email, phone_number, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        (
            data.full_name,
            data.email,
            data.phone_number,
            generate_password_hash(data.password),
        ),
    )
    database.commit()
    return int(cursor.lastrowid)


@bp.route("/job-seeker/register", methods=("GET", "POST"))
def register():
    """Display and process the job seeker registration form."""
    errors: dict[str, str] = {}
    form_data = {"full_name": "", "email": "", "phone_number": ""}

    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        expected_token = session.get("csrf_token", "")
        if not expected_token or not hmac.compare_digest(
            submitted_token, expected_token
        ):
            errors["form"] = (
                "Your form session expired. Refresh the page and try again."
            )
        else:
            data = _registration_data(request.form)
            form_data = {
                "full_name": data.full_name,
                "email": data.email,
                "phone_number": data.phone_number,
            }
            errors = _validate(data)

            if not errors:
                try:
                    _create_job_seeker(data)
                except sqlite3.IntegrityError:
                    errors["email"] = (
                        "An account with this email address already exists."
                    )
                else:
                    session.pop("csrf_token", None)
                    flash(
                        "Your job seeker account was created successfully.", "success"
                    )
                    return redirect(url_for("job_seeker.register_success"))

    status_code = 400 if request.method == "POST" and errors else 200
    return (
        render_template(
            "job_seeker_register.html",
            csrf_token=_csrf_token(),
            errors=errors,
            form_data=form_data,
        ),
        status_code,
    )


@bp.get("/job-seeker/register/success")
def register_success():
    """Display registration confirmation after a successful redirect."""
    return render_template("registration_success.html")


@bp.post("/api/job-seekers/register")
def register_api():
    """Create a job seeker from a JSON client."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"message": "A JSON request body is required."}), 400

    data = _registration_data(payload)
    errors = _validate(data)
    if errors:
        return (
            jsonify({"message": "Registration validation failed.", "errors": errors}),
            422,
        )

    try:
        job_seeker_id = _create_job_seeker(data)
    except sqlite3.IntegrityError:
        return (
            jsonify(
                {
                    "message": "Registration validation failed.",
                    "errors": {
                        "email": "An account with this email address already exists."
                    },
                }
            ),
            409,
        )

    return (
        jsonify(
            {
                "message": "Job seeker account created successfully.",
                "job_seeker": {"id": job_seeker_id, "email": data.email},
            }
        ),
        201,
    )
