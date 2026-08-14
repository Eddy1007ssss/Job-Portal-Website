from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.application_history import (
    SORT_OPTIONS,
    STATUS_OPTIONS,
    get_application_history,
    parse_application_history_options,
)
from src.application_submission import (
    can_submit_application,
    submit_application,
)
from src.application_withdrawal import withdraw_application
from src.database import get_db_connection
from src.employer_notifications import (
    sync_employer_activity_for_application,
)

applications_bp = Blueprint(
    "applications",
    __name__,
    url_prefix="/applications",
)

COVER_LETTER_MIN_LENGTH = 50
COVER_LETTER_MAX_LENGTH = 2000


@applications_bp.route("/")
def list_applications():
    seeker_id = session.get("seeker_id")

    if not seeker_id or session.get("seeker_authenticated") is not True:
        flash(
            "Please log in as a job seeker to view your application history.",
            "error",
        )
        return redirect(url_for("seeker.login"))

    options = parse_application_history_options(
        request.args.get("status"),
        request.args.get("sort"),
    )

    connection = get_db_connection()
    applications, total_application_count = get_application_history(
        connection,
        int(seeker_id),
        options,
    )
    connection.close()

    return render_template(
        "my_applications.html",
        applications=applications,
        total_application_count=total_application_count,
        selected_status=options.status_key,
        selected_sort=options.sort_key,
        filters_active=options.filters_active,
        status_options=STATUS_OPTIONS,
        sort_options=SORT_OPTIONS,
    )


@applications_bp.post("/<int:application_id>/withdraw")
def withdraw_job_application(application_id: int):
    seeker_id = session.get("seeker_id")

    if not seeker_id or session.get("seeker_authenticated") is not True:
        flash(
            "Please log in as a job seeker to withdraw an application.",
            "error",
        )
        return redirect(url_for("seeker.login"))

    connection = get_db_connection()
    result = withdraw_application(
        connection,
        application_id,
        int(seeker_id),
    )

    if result.succeeded:
        sync_employer_activity_for_application(
            connection,
            application_id,
        )

    connection.close()

    if result.succeeded:
        flash("Application withdrawn successfully.", "success")
    elif result.outcome == "not_found":
        flash("Application was not found.", "error")
    else:
        flash(
            "Only applications that are still Pending can be withdrawn.",
            "error",
        )

    return redirect(url_for("applications.list_applications"))


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
        return redirect(url_for("jobs.list_jobs"))

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
        SELECT status
        FROM applications
        WHERE seeker_id = ?
          AND job_id = ?
        """,
        (
            seeker_id,
            job_id,
        ),
    ).fetchone()

    existing_status = (
        existing_application["status"] if existing_application is not None else None
    )

    if not can_submit_application(existing_status):
        connection.close()

        if existing_status == "Rejected":
            message = (
                "Your previous application for this job was rejected. "
                "You cannot apply again to the same job posting."
            )
        else:
            message = "You have already applied for this job."

        flash(message, "warning")
        return redirect(
            url_for(
                "jobs.job_details",
                job_id=job_id,
            )
        )

    cover_letter = request.form.get("cover_letter", "").strip()

    if not cover_letter:
        connection.close()

        flash(
            "Please write a cover letter before applying.",
            "error",
        )
        return redirect(
            url_for(
                "jobs.job_details",
                job_id=job_id,
            )
        )

    if len(cover_letter) < COVER_LETTER_MIN_LENGTH:
        connection.close()

        flash(
            "Cover letter must contain at least 50 characters.",
            "error",
        )
        return redirect(
            url_for(
                "jobs.job_details",
                job_id=job_id,
            )
        )

    if len(cover_letter) > COVER_LETTER_MAX_LENGTH:
        connection.close()

        flash(
            "Cover letter must not exceed 2000 characters.",
            "error",
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

    resume_filename = seeker_profile["resume_filename"] if seeker_profile else None

    result = submit_application(
        connection,
        int(seeker_id),
        job_id,
        cover_letter,
        resume_filename,
    )

    if result.succeeded and result.application_id is not None:
        sync_employer_activity_for_application(
            connection,
            result.application_id,
        )

    connection.close()

    if result.outcome == "reapplied":
        flash(
            "Your application was submitted again successfully.",
            "success",
        )
    elif result.outcome == "submitted":
        flash(
            "Your job application was submitted successfully.",
            "success",
        )
    else:
        flash(
            "This application can no longer be submitted again.",
            "warning",
        )

    return redirect(
        url_for(
            "jobs.job_details",
            job_id=job_id,
        )
    )
