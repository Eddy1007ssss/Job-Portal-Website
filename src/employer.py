import re
from functools import wraps
from typing import Callable

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from src.database import get_db_connection

employer_bp = Blueprint("employer", __name__)

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

PHONE_PATTERN = re.compile(r"^[0-9+\-\s]{8,15}$")


def employer_login_required(view_function: Callable) -> Callable:
    """
    Protect employer-only pages.

    An employer must be logged in before accessing the route.
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if session.get("employer_id") is None:
            flash(
                "Please log in as an employer first.",
                "error",
            )
            return redirect(url_for("employer.login"))

        return view_function(*args, **kwargs)

    return wrapped_view


def get_employer(employer_id: int):
    """
    Retrieve one employer account.
    """

    connection = get_db_connection()

    employer = connection.execute(
        """
        SELECT
            employer_id,
            company_name,
            company_email,
            contact_number,
            created_at
        FROM employers
        WHERE employer_id = ?
        """,
        (employer_id,),
    ).fetchone()

    connection.close()

    return employer


def get_company_profile(employer_id: int):
    """
    Retrieve one employer's company profile.
    """

    connection = get_db_connection()

    profile = connection.execute(
        """
        SELECT
            company_profiles.*,
            employers.company_email
        FROM company_profiles
        JOIN employers
            ON company_profiles.employer_id =
               employers.employer_id
        WHERE company_profiles.employer_id = ?
        """,
        (employer_id,),
    ).fetchone()

    connection.close()

    return profile


@employer_bp.route(
    "/employer/register",
    methods=["GET", "POST"],
)
def register():
    """
    Register a new employer account.

    After registration, the employer is logged in and redirected
    to the company profile creation form.
    """

    if session.get("employer_id") is not None:
        profile = get_company_profile(session["employer_id"])

        if profile is not None:
            return redirect(url_for("employer.company_preview"))

        return redirect(url_for("employer.company_profile"))

    if request.method == "POST":
        company_name = request.form.get(
            "company_name",
            "",
        ).strip()

        company_email = (
            request.form.get(
                "company_email",
                "",
            )
            .strip()
            .lower()
        )

        contact_number = request.form.get(
            "contact_number",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        confirm_password = request.form.get(
            "confirm_password",
            "",
        )

        errors = []

        if len(company_name) < 2:
            errors.append("Company name must contain at least " "2 characters.")

        if not EMAIL_PATTERN.fullmatch(company_email):
            errors.append("Please enter a valid company email.")

        if not PHONE_PATTERN.fullmatch(contact_number):
            errors.append(
                "Contact number must contain between "
                "8 and 15 characters and may include "
                "numbers, spaces, + or -."
            )

        if len(password) < 8:
            errors.append("Password must contain at least " "8 characters.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        connection = get_db_connection()

        existing_employer = connection.execute(
            """
            SELECT employer_id
            FROM employers
            WHERE company_email = ?
            """,
            (company_email,),
        ).fetchone()

        if existing_employer is not None:
            errors.append("This company email is already registered.")

        if errors:
            connection.close()

            for error in errors:
                flash(error, "error")

            return render_template(
                "employer_register.html",
                company_name=company_name,
                company_email=company_email,
                contact_number=contact_number,
            )

        cursor = connection.execute(
            """
            INSERT INTO employers (
                company_name,
                company_email,
                contact_number,
                password_hash
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                company_name,
                company_email,
                contact_number,
                generate_password_hash(password),
            ),
        )

        employer_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

        session.clear()
        session["employer_id"] = employer_id
        session["employer_company_name"] = company_name
        session["employer_email"] = company_email

        flash(
            "Employer account created successfully. "
            "Please complete your company profile.",
            "success",
        )

        return redirect(url_for("employer.company_profile"))

    return render_template("employer_register.html")


@employer_bp.route(
    "/employer/login",
    methods=["GET", "POST"],
)
def login():
    """
    Log in an employer.

    Existing company profile:
        Login -> Company profile view

    Missing company profile:
        Login -> Create company profile form
    """

    if session.get("employer_id") is not None:
        profile = get_company_profile(session["employer_id"])

        if profile is not None:
            return redirect(url_for("employer.company_preview"))

        return redirect(url_for("employer.company_profile"))

    if request.method == "POST":
        company_email = (
            request.form.get(
                "company_email",
                "",
            )
            .strip()
            .lower()
        )

        password = request.form.get(
            "password",
            "",
        )

        connection = get_db_connection()

        employer = connection.execute(
            """
            SELECT *
            FROM employers
            WHERE company_email = ?
            """,
            (company_email,),
        ).fetchone()

        if employer is None or not check_password_hash(
            employer["password_hash"],
            password,
        ):
            connection.close()

            flash(
                "Incorrect email or password.",
                "error",
            )

            return render_template(
                "employer_login.html",
                company_email=company_email,
            )

        company_profile = connection.execute(
            """
            SELECT profile_id
            FROM company_profiles
            WHERE employer_id = ?
            """,
            (employer["employer_id"],),
        ).fetchone()

        connection.close()

        session.clear()
        session["employer_id"] = employer["employer_id"]
        session["employer_company_name"] = employer["company_name"]
        session["employer_email"] = employer["company_email"]

        flash(
            "Login successful.",
            "success",
        )

        if company_profile is None:
            flash(
                "Please complete your company profile.",
                "error",
            )

            return redirect(url_for("employer.company_profile"))

        return redirect(url_for("employer.company_preview"))

    return render_template("employer_login.html")


@employer_bp.route("/employer/logout")
def logout():
    """
    Log out the current employer.
    """

    session.clear()

    flash(
        "You have logged out successfully.",
        "success",
    )

    return redirect(url_for("employer.login"))


@employer_bp.route(
    "/employer/company-profile",
    methods=["GET", "POST"],
)
@employer_login_required
def company_profile():
    """
    Create or edit the current employer's company profile.
    """

    employer_id = int(session["employer_id"])

    connection = get_db_connection()

    employer = connection.execute(
        """
        SELECT
            employer_id,
            company_name,
            company_email,
            contact_number,
            created_at
        FROM employers
        WHERE employer_id = ?
        """,
        (employer_id,),
    ).fetchone()

    existing_profile = connection.execute(
        """
        SELECT *
        FROM company_profiles
        WHERE employer_id = ?
        """,
        (employer_id,),
    ).fetchone()

    if employer is None:
        connection.close()
        session.clear()

        flash(
            "Employer account was not found.",
            "error",
        )

        return redirect(url_for("employer.login"))

    if request.method == "POST":
        company_name = request.form.get(
            "company_name",
            "",
        ).strip()

        industry = request.form.get(
            "industry",
            "",
        ).strip()

        company_size = request.form.get(
            "company_size",
            "",
        ).strip()

        address = request.form.get(
            "address",
            "",
        ).strip()

        company_description = request.form.get(
            "company_description",
            "",
        ).strip()

        contact_email = (
            request.form.get(
                "contact_email",
                "",
            )
            .strip()
            .lower()
        )

        contact_number = request.form.get(
            "contact_number",
            "",
        ).strip()

        website = request.form.get(
            "website",
            "",
        ).strip()

        logo_url = request.form.get(
            "logo_url",
            "",
        ).strip()

        banner_url = request.form.get(
            "banner_url",
            "",
        ).strip()

        errors = []

        if len(company_name) < 2:
            errors.append("Company name must contain at least " "2 characters.")

        if not industry:
            errors.append("Please select an industry.")

        if len(address) < 5:
            errors.append("Please enter the complete company address.")

        if len(company_description) < 30:
            errors.append("Company description must contain at least " "30 characters.")

        if len(company_description) > 1500:
            errors.append("Company description cannot exceed " "1500 characters.")

        if not EMAIL_PATTERN.fullmatch(contact_email):
            errors.append("Please enter a valid contact email.")

        if not PHONE_PATTERN.fullmatch(contact_number):
            errors.append(
                "Contact number must contain between "
                "8 and 15 characters and may include "
                "numbers, spaces, + or -."
            )

        submitted_profile = {
            "company_name": company_name,
            "industry": industry,
            "company_size": company_size,
            "address": address,
            "company_description": company_description,
            "contact_email": contact_email,
            "contact_number": contact_number,
            "website": website,
            "logo_url": logo_url,
            "banner_url": banner_url,
        }

        if errors:
            connection.close()

            for error in errors:
                flash(error, "error")

            return render_template(
                "employer_company_profile.html",
                employer=employer,
                profile=submitted_profile,
                profile_exists=(existing_profile is not None),
            )

        profile_values = (
            company_name,
            industry,
            address,
            company_description,
            contact_email,
            contact_number,
            website,
            company_size,
            logo_url,
            banner_url,
        )

        if existing_profile is not None:
            connection.execute(
                """
                UPDATE company_profiles
                SET
                    company_name = ?,
                    industry = ?,
                    address = ?,
                    company_description = ?,
                    contact_email = ?,
                    contact_number = ?,
                    website = ?,
                    company_size = ?,
                    logo_url = ?,
                    banner_url = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE employer_id = ?
                """,
                (
                    *profile_values,
                    employer_id,
                ),
            )

            success_message = "Company profile updated successfully."
        else:
            connection.execute(
                """
                INSERT INTO company_profiles (
                    employer_id,
                    company_name,
                    industry,
                    address,
                    company_description,
                    contact_email,
                    contact_number,
                    website,
                    company_size,
                    logo_url,
                    banner_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    employer_id,
                    *profile_values,
                ),
            )

            success_message = "Company profile created successfully."

        connection.execute(
            """
            UPDATE employers
            SET
                company_name = ?,
                contact_number = ?
            WHERE employer_id = ?
            """,
            (
                company_name,
                contact_number,
                employer_id,
            ),
        )

        connection.commit()
        connection.close()

        session["employer_company_name"] = company_name
        session["employer_email"] = employer["company_email"]

        flash(
            success_message,
            "success",
        )

        return redirect(url_for("employer.company_preview"))

    connection.close()

    return render_template(
        "employer_company_profile.html",
        employer=employer,
        profile=existing_profile,
        profile_exists=(existing_profile is not None),
    )


@employer_bp.route("/employer/company-profile/preview")
@employer_login_required
def company_preview():
    """
    Display the current employer's company profile.
    """

    employer_id = int(session["employer_id"])

    profile = get_company_profile(employer_id)

    if profile is None:
        flash(
            "Please create your company profile first.",
            "error",
        )

        return redirect(url_for("employer.company_profile"))

    return render_template(
        "company_profile.html",
        company=profile,
        preview_mode=True,
        employer_view=True,
    )


@employer_bp.route("/companies/<int:employer_id>")
def public_company_profile(employer_id: int):
    """
    Display a public company profile to job seekers
    and visitors.
    """

    profile = get_company_profile(employer_id)

    if profile is None:
        return render_template("error.html"), 404

    return render_template(
        "company_profile.html",
        company=profile,
        preview_mode=False,
        employer_view=False,
    )
