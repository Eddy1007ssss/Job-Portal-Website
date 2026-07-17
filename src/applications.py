from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)

from src.database import get_db_connection


applications_bp = Blueprint(
    "applications",
    __name__,
    url_prefix="/applications",
)


@applications_bp.route("/")
def list_applications():
    seeker_id = session.get("seeker_id")

    if not seeker_id:
        flash(
            "A job seeker profile is required to view applications.",
            "warning",
        )
        return redirect(
            url_for("seeker.profile")
        )

    connection = get_db_connection()

    applications = connection.execute(
        """
        SELECT
            applications.application_id,
            applications.status AS application_status,
            applications.resume_filename,
            applications.created_at,
            jobs.job_id,
            jobs.job_title,
            jobs.location,
            jobs.employment_type,
            employers.company_name
        FROM applications
        JOIN jobs
            ON jobs.job_id = applications.job_id
        JOIN employers
            ON employers.employer_id = jobs.employer_id
        WHERE applications.seeker_id = ?
        ORDER BY applications.application_id DESC
        """,
        (seeker_id,),
    ).fetchall()

    connection.close()

    return render_template(
        "my_applications.html",
        applications=applications,
    )


@applications_bp.route(
    "/jobs/<int:job_id>/apply",
    methods=["POST"],
)
def apply_job(job_id: int):
    seeker_id = session.get("seeker_id")

    if not seeker_id:
        flash(
            "A job seeker profile is required to apply.",
            "warning",
        )
        return redirect(
            url_for(
                "jobs.job_details",
                job_id=job_id,
            )
        )

    connection = get_db_connection()

    job = connection.execute(
        """
        SELECT
            job_id,
            status
        FROM jobs
        WHERE job_id = ?
        """,
        (job_id,),
    ).fetchone()

    if job is None:
        connection.close()

        flash(
            "The selected job does not exist.",
            "error",
        )
        return redirect(
            url_for("jobs.list_jobs")
        )

    if job["status"] != "Open":
        connection.close()

        flash(
            "This job is no longer accepting applications.",
            "warning",
        )
        return redirect(
            url_for(
                "jobs.job_details",
                job_id=job_id,
            )
        )

    existing_application = connection.execute(
        """
        SELECT application_id
        FROM applications
        WHERE seeker_id = ?
          AND job_id = ?
        """,
        (
            seeker_id,
            job_id,
        ),
    ).fetchone()

    if existing_application:
        connection.close()

        flash(
            "You have already applied for this job.",
            "warning",
        )
        return redirect(
            url_for(
                "jobs.job_details",
                job_id=job_id,
            )
        )

    seeker_profile = connection.execute(
        """
        SELECT resume_filename
        FROM seeker_profiles
        WHERE seeker_id = ?
        """,
        (seeker_id,),
    ).fetchone()

    resume_filename = (
        seeker_profile["resume_filename"]
        if seeker_profile
        else None
    )

    connection.execute(
        """
        INSERT INTO applications (
            seeker_id,
            job_id,
            resume_filename,
            status
        )
        VALUES (?, ?, ?, 'Pending')
        """,
        (
            seeker_id,
            job_id,
            resume_filename,
        ),
    )

    connection.commit()
    connection.close()

    flash(
        "Your job application was submitted successfully.",
        "success",
    )

    return redirect(
        url_for(
            "jobs.job_details",
            job_id=job_id,
        )
    )