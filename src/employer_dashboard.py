from functools import wraps

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)

from src.database import get_db_connection

employer_dashboard_bp = Blueprint(
    "employer_dashboard",
    __name__,
)


def employer_login_required(view_function):
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


@employer_dashboard_bp.route("/employer/dashboard")
@employer_login_required
def dashboard():
    employer_id = int(session["employer_id"])

    connection = get_db_connection()

    total_job_postings = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM jobs
        WHERE employer_id = ?
        """,
        (employer_id,),
    ).fetchone()["total"]

    active_vacancies = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM jobs
        WHERE employer_id = ?
          AND LOWER(status) IN ('open', 'active')
        """,
        (employer_id,),
    ).fetchone()["total"]

    closed_vacancies = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM jobs
        WHERE employer_id = ?
          AND LOWER(status) IN ('closed', 'expired')
        """,
        (employer_id,),
    ).fetchone()["total"]

    total_applications = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM applications
        JOIN jobs
            ON jobs.job_id = applications.job_id
        WHERE jobs.employer_id = ?
        """,
        (employer_id,),
    ).fetchone()["total"]

    recent_jobs = connection.execute(
        """
        SELECT
            jobs.job_id,
            jobs.title,
            jobs.location,
            jobs.employment_type,
            jobs.status,
            jobs.created_at,
            COUNT(applications.application_id)
                AS application_count
        FROM jobs
        LEFT JOIN applications
            ON applications.job_id = jobs.job_id
        WHERE jobs.employer_id = ?
        GROUP BY jobs.job_id
        ORDER BY jobs.created_at DESC
        LIMIT 5
        """,
        (employer_id,),
    ).fetchall()

    recent_applicants = connection.execute(
        """
        SELECT
            applications.application_id,
            applications.applied_at,
            applications.status,
            applications.job_id,

            seekers.full_name AS applicant_name,
            seekers.email AS applicant_email,

            jobs.title AS job_title

        FROM applications

        JOIN seekers
            ON seekers.seeker_id = applications.seeker_id

        JOIN jobs
            ON jobs.job_id = applications.job_id

        WHERE jobs.employer_id = ?

        ORDER BY applications.applied_at DESC

        LIMIT 5
        """,
        (employer_id,),
    ).fetchall()

    connection.close()

    statistics = {
        "total_job_postings": total_job_postings,
        "active_vacancies": active_vacancies,
        "closed_vacancies": closed_vacancies,
        "total_applications": total_applications,
    }

    return render_template(
        "employer_dashboard.html",
        statistics=statistics,
        recent_jobs=recent_jobs,
        recent_applicants=recent_applicants,
    )
