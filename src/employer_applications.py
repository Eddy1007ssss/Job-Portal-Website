from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.database import get_db_connection

employer_applications_bp = Blueprint(
    "employer_applications",
    __name__,
)


APPLICATION_STATUSES = (
    "Pending",
    "Shortlisted",
    "Rejected",
    "Accepted",
)


# =========================================================
# Employer authentication
# =========================================================


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


# =========================================================
# Job ownership helper
# =========================================================


def get_owned_job(
    employer_id: int,
    job_id: int,
):
    """
    Return a job only if it belongs to the logged-in employer.
    """

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
            vacancies,
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


# =========================================================
# Employer application list
# =========================================================


@employer_applications_bp.route("/employer/jobs/<int:job_id>/applications")
@employer_login_required
def application_list(job_id: int):
    """
    Display all applications submitted for one
    employer-owned job.
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
            seeker_profiles.location
                AS applicant_location,
            seeker_profiles.profile_image,

            COALESCE(
                applications.resume_filename,
                seeker_profiles.resume_filename
            ) AS available_resume

        FROM applications

        JOIN seekers
            ON seekers.seeker_id =
               applications.seeker_id

        LEFT JOIN seeker_profiles
            ON seeker_profiles.seeker_id =
               seekers.seeker_id

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
        application_statuses=APPLICATION_STATUSES,
    )


# =========================================================
# Update application status
# =========================================================


@employer_applications_bp.post("/employer/applications/" "<int:application_id>/status")
@employer_login_required
def update_application_status(
    application_id: int,
):
    """
    Update an employer-owned application status.

    When changing an application to Accepted:
    1. Check the job vacancy limit.
    2. Prevent accepting more applicants than vacancies.
    3. Automatically close the job when all vacancies
       have been filled.
    """

    employer_id = int(session["employer_id"])

    target_status = request.form.get(
        "status",
        "",
    ).strip()

    connection = get_db_connection()

    # -----------------------------------------------------
    # Retrieve the application and associated job
    # -----------------------------------------------------

    application = connection.execute(
        """
        SELECT
            applications.application_id,
            applications.job_id,
            applications.status
                AS current_status,

            jobs.title AS job_title,
            jobs.status AS job_status,
            jobs.vacancies

        FROM applications

        JOIN jobs
            ON jobs.job_id =
               applications.job_id

        WHERE applications.application_id = ?
          AND jobs.employer_id = ?
        """,
        (
            application_id,
            employer_id,
        ),
    ).fetchone()

    # -----------------------------------------------------
    # Application ownership validation
    # -----------------------------------------------------

    if application is None:
        connection.close()
        abort(404)

    job_id = int(application["job_id"])

    # -----------------------------------------------------
    # Application status validation
    # -----------------------------------------------------

    if target_status not in APPLICATION_STATUSES:
        connection.close()

        flash(
            "Select a valid application status.",
            "error",
        )

        return redirect(
            url_for(
                "employer_applications.application_list",
                job_id=job_id,
            )
        )

    current_status = str(application["current_status"] or "").strip()

    job_status = str(application["job_status"] or "").strip()

    try:
        vacancies = int(application["vacancies"])
    except TypeError, ValueError:
        vacancies = 1

    vacancies = max(vacancies, 1)

    # -----------------------------------------------------
    # Vacancy validation when accepting an applicant
    # -----------------------------------------------------

    if target_status == "Accepted" and current_status != "Accepted":
        accepted_result = connection.execute(
            """
            SELECT
                COUNT(*) AS total
            FROM applications
            WHERE job_id = ?
              AND LOWER(status) = 'accepted'
            """,
            (job_id,),
        ).fetchone()

        accepted_count = int(accepted_result["total"])

        # Job already has enough accepted applicants.
        if accepted_count >= vacancies:
            connection.close()

            flash(
                (
                    "This job has already reached "
                    "its vacancy limit. No more "
                    "applicants can be accepted."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "employer_applications." "application_list",
                    job_id=job_id,
                )
            )

        # Prevent accepting new applicants for a manually
        # closed job unless it was closed because capacity
        # was already full.
        if job_status.lower() == "closed":
            connection.close()

            flash(
                (
                    "This job posting is already "
                    "closed. Reopen the job before "
                    "accepting another applicant."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "employer_applications." "application_list",
                    job_id=job_id,
                )
            )

    # -----------------------------------------------------
    # Update application status
    # -----------------------------------------------------

    connection.execute(
        """
        UPDATE applications
        SET
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (
            target_status,
            application_id,
        ),
    )

    # -----------------------------------------------------
    # Check vacancy capacity after acceptance
    # -----------------------------------------------------

    if target_status == "Accepted":
        accepted_result = connection.execute(
            """
            SELECT
                COUNT(*) AS total
            FROM applications
            WHERE job_id = ?
              AND LOWER(status) = 'accepted'
            """,
            (job_id,),
        ).fetchone()

        accepted_count = int(accepted_result["total"])

        # -------------------------------------------------
        # Automatically close job if capacity is full
        # -------------------------------------------------

        if accepted_count >= vacancies:
            connection.execute(
                """
                UPDATE jobs
                SET
                    status = 'Closed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                  AND employer_id = ?
                """,
                (
                    job_id,
                    employer_id,
                ),
            )

            connection.commit()
            connection.close()

            flash(
                (
                    "Application accepted successfully. "
                    f"The job has filled all "
                    f"{vacancies} "
                    f"vacanc"
                    f"{'y' if vacancies == 1 else 'ies'} "
                    "and has been closed automatically."
                ),
                "success",
            )

            return redirect(
                url_for(
                    "employer_applications." "application_list",
                    job_id=job_id,
                )
            )

    connection.commit()
    connection.close()

    flash(
        ("Application status updated to " f"{target_status}."),
        "success",
    )

    return redirect(
        url_for(
            "employer_applications." "application_list",
            job_id=job_id,
        )
    )


# =========================================================
# Applicant details
# =========================================================


@employer_applications_bp.route("/employer/applications/" "<int:application_id>")
@employer_login_required
def application_details(
    application_id: int,
):
    """
    Display one applicant's details.

    The application is returned only if the associated
    job belongs to the currently logged-in employer.
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
            jobs.status AS job_status,
            jobs.vacancies,

            seekers.full_name
                AS applicant_name,
            seekers.email
                AS applicant_email,
            seekers.contact_number
                AS applicant_contact,

            seeker_profiles.job_title
                AS applicant_job_title,
            seeker_profiles.location
                AS applicant_location,
            seeker_profiles.about_me,
            seeker_profiles.profile_image,

            COALESCE(
                applications.resume_filename,
                seeker_profiles.resume_filename
            ) AS available_resume

        FROM applications

        JOIN jobs
            ON jobs.job_id =
               applications.job_id

        JOIN seekers
            ON seekers.seeker_id =
               applications.seeker_id

        LEFT JOIN seeker_profiles
            ON seeker_profiles.seeker_id =
               seekers.seeker_id

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

    # -----------------------------------------------------
    # Applicant skills
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Applicant education
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Applicant work experience
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Applicant languages
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Applicant certificates
    # -----------------------------------------------------

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
