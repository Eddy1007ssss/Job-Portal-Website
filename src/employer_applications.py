from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)

from src.database import get_db_connection


employer_applications_bp = Blueprint(
    "employer_applications",
    __name__,
)


def employer_login_required(view_function: Callable) -> Callable:
    """Protect employer-only application pages."""

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


def get_owned_job(
    employer_id: int,
    job_id: int,
):
    """Return a job only if it belongs to the logged-in employer."""

    connection = get_db_connection()

    job = connection.execute(
        """
        SELECT
            job_id,
            employer_id,
            title,
            location,
            employment_type,
            status,
            created_at,
            application_deadline
        FROM jobs
        WHERE job_id = ?
          AND employer_id = ?
        """,
        (
            job_id,
            employer_id,
        ),
    ).fetchone()

    connection.close()

    return job


@employer_applications_bp.route(
    "/employer/jobs/<int:job_id>/applications"
)
@employer_login_required
def application_list(job_id: int):
    """
    Display all applications submitted for one employer-owned job.
    """

    employer_id = int(session["employer_id"])

    job = get_owned_job(
        employer_id=employer_id,
        job_id=job_id,
    )

    if job is None:
        flash(
            "The selected job posting was not found.",
            "error",
        )
        return redirect(url_for("jobs.employer_jobs"))

    connection = get_db_connection()

    applications = connection.execute(
        """
        SELECT
            applications.application_id,
            applications.job_id,
            applications.seeker_id,
            applications.status,
            applications.applied_at,
            applications.updated_at,
            applications.resume_filename,

            seekers.full_name AS applicant_name,
            seekers.email AS applicant_email,
            seekers.contact_number AS applicant_contact,

            seeker_profiles.job_title,
            seeker_profiles.location AS applicant_location,
            seeker_profiles.profile_image,

            COALESCE(
                applications.resume_filename,
                seeker_profiles.resume_filename
            ) AS available_resume

        FROM applications

        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id

        LEFT JOIN seeker_profiles
            ON seeker_profiles.seeker_id = seekers.seeker_id

        WHERE applications.job_id = ?

        ORDER BY applications.applied_at DESC
        """,
        (job_id,),
    ).fetchall()

    status_counts = {
        "all": len(applications),
        "pending": 0,
        "reviewing": 0,
        "shortlisted": 0,
        "accepted": 0,
        "rejected": 0,
    }

    for application in applications:
        status = application["status"]

        if status is None:
            continue

        status_key = str(status).strip().lower()

        if status_key in status_counts:
            status_counts[status_key] += 1

    connection.close()

    return render_template(
        "employer_application_list.html",
        job=job,
        applications=applications,
        status_counts=status_counts,
    )


@employer_applications_bp.route(
    "/employer/applications/<int:application_id>"
)
@employer_login_required
def application_details(application_id: int):
    """
    Display one applicant's details.

    The application is returned only if the associated job belongs
    to the currently logged-in employer.
    """

    employer_id = int(session["employer_id"])

    connection = get_db_connection()

    application_row = connection.execute(
        """
        SELECT
            applications.application_id,
            applications.job_id,
            applications.seeker_id,
            applications.cover_letter,
            applications.resume_filename,
            applications.status,
            applications.applied_at,
            applications.updated_at,

            jobs.title AS job_title,
            jobs.location AS job_location,

            seekers.full_name AS applicant_name,
            seekers.email AS applicant_email,
            seekers.contact_number AS applicant_contact,

            seeker_profiles.job_title AS applicant_job_title,
            seeker_profiles.location AS applicant_location,
            seeker_profiles.about_me,
            seeker_profiles.profile_image,

            COALESCE(
                applications.resume_filename,
                seeker_profiles.resume_filename
            ) AS available_resume

        FROM applications

        JOIN jobs
            ON jobs.job_id = applications.job_id

        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id

        LEFT JOIN seeker_profiles
            ON seeker_profiles.seeker_id = seekers.seeker_id

        WHERE applications.application_id = ?
          AND jobs.employer_id = ?
        """,
        (
            application_id,
            employer_id,
        ),
    ).fetchone()

    if application_row is None:
        connection.close()
        abort(404)

    seeker_id = int(application_row["seeker_id"])

    skills = connection.execute(
        """
        SELECT
            skill_id,
            skill_name
        FROM seeker_skills
        WHERE seeker_id = ?
        ORDER BY skill_name
        """,
        (seeker_id,),
    ).fetchall()

    education_items = connection.execute(
        """
        SELECT
            education_id,
            qualification,
            institution,
            start_year,
            end_year,
            status
        FROM seeker_education
        WHERE seeker_id = ?
        ORDER BY education_id DESC
        """,
        (seeker_id,),
    ).fetchall()

    experiences = connection.execute(
        """
        SELECT
            experience_id,
            position_title,
            company_name,
            start_date,
            end_date,
            description
        FROM seeker_experiences
        WHERE seeker_id = ?
        ORDER BY experience_id DESC
        """,
        (seeker_id,),
    ).fetchall()

    languages = connection.execute(
        """
        SELECT
            language_id,
            language_name,
            proficiency
        FROM seeker_languages
        WHERE seeker_id = ?
        ORDER BY language_name
        """,
        (seeker_id,),
    ).fetchall()

    certificates = connection.execute(
        """
        SELECT
            certificate_id,
            certificate_name,
            issuer,
            issue_date,
            certificate_filename,
            original_filename
        FROM seeker_certificates
        WHERE seeker_id = ?
        ORDER BY certificate_id DESC
        """,
        (seeker_id,),
    ).fetchall()

    connection.close()

    application = dict(application_row)

    application["skills"] = skills
    application["education_items"] = education_items
    application["experiences"] = experiences
    application["languages"] = languages
    application["certificates"] = certificates

    return render_template(
        "employer_application_details.html",
        application=application,
    )