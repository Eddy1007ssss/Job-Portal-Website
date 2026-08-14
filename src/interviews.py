from datetime import datetime, timedelta

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
from src.employer_notifications import sync_employer_activity_for_interview
from src.interview_management import (
    INTERVIEW_MODES,
    INTERVIEW_STATUSES,
    MALAYSIA_TIMEZONE,
    InterviewDetails,
    cancel_interview,
    complete_interview,
    get_employer_interviews,
    get_interview_application,
    get_seeker_interviews,
    respond_to_interview,
    save_interview,
)

interviews_bp = Blueprint("interviews", __name__)


@interviews_bp.get("/interviews")
def seeker_interviews():
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        flash("Please log in as a job seeker to view interviews.", "error")
        return redirect(url_for("seeker.login"))

    connection = get_db_connection()
    interviews = get_seeker_interviews(connection, seeker_id)
    connection.close()
    summary = {
        "total": len(interviews),
        "pending": sum(item["status"] == "Pending" for item in interviews),
        "accepted": sum(item["status"] == "Accepted" for item in interviews),
        "upcoming": sum(
            item["is_upcoming"] and item["status"] in {"Pending", "Accepted"}
            for item in interviews
        ),
    }
    return render_template(
        "seeker_interviews.html",
        interviews=interviews,
        summary=summary,
    )


@interviews_bp.post("/interviews/<int:interview_id>/respond")
def respond(interview_id: int):
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        flash("Please log in as a job seeker to respond.", "error")
        return redirect(url_for("seeker.login"))

    connection = get_db_connection()
    result = respond_to_interview(
        connection,
        seeker_id,
        interview_id,
        request.form.get("response", "").strip(),
        request.form.get("reason", "").strip(),
    )

    if result.succeeded:
        sync_employer_activity_for_interview(
            connection,
            interview_id,
        )

    connection.close()
    flash(result.message, "success" if result.succeeded else "error")
    return redirect(url_for("interviews.seeker_interviews"))


@interviews_bp.get("/employer/interviews")
def employer_interviews():
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        flash("Please log in as an employer first.", "error")
        return redirect(url_for("employer.login"))

    selected_status = request.args.get("status", "all").strip().title()
    query_status = selected_status if selected_status in INTERVIEW_STATUSES else None

    if query_status is None:
        selected_status = "All"

    connection = get_db_connection()
    interviews = get_employer_interviews(
        connection,
        employer_id,
        query_status,
    )
    all_interviews = get_employer_interviews(connection, employer_id)
    connection.close()
    summary = {
        "total": len(all_interviews),
        "pending": sum(item["status"] == "Pending" for item in all_interviews),
        "accepted": sum(item["status"] == "Accepted" for item in all_interviews),
        "completed": sum(item["status"] == "Completed" for item in all_interviews),
    }
    return render_template(
        "employer_interviews.html",
        interviews=interviews,
        summary=summary,
        selected_status=selected_status,
        status_options=INTERVIEW_STATUSES,
    )


@interviews_bp.route(
    "/employer/applications/<int:application_id>/interview",
    methods=["GET", "POST"],
)
def manage_interview(application_id: int):
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        flash("Please log in as an employer first.", "error")
        return redirect(url_for("employer.login"))

    connection = get_db_connection()
    application, interview = get_interview_application(
        connection,
        employer_id,
        application_id,
    )

    if application is None:
        connection.close()
        abort(404)

    if request.method == "POST":
        details = _interview_form_details()
        result = save_interview(
            connection,
            employer_id,
            application_id,
            details,
        )

        if result.succeeded:
            connection.close()
            flash(result.message, "success")
            return redirect(url_for("interviews.employer_interviews"))

        connection.close()
        flash(result.message, "error")
        form_data = {
            "scheduled_date": details.scheduled_date,
            "scheduled_time": details.scheduled_time,
            "duration_minutes": details.duration_minutes,
            "interview_mode": details.interview_mode,
            "location_or_link": details.location_or_link,
            "notes": details.notes,
        }
    else:
        connection.close()
        form_data = _interview_form_defaults(interview)

    today = datetime.now(MALAYSIA_TIMEZONE).date()
    return render_template(
        "employer_interview_form.html",
        application=application,
        interview=interview,
        form_data=form_data,
        interview_modes=INTERVIEW_MODES,
        minimum_date=today.isoformat(),
        maximum_date=(today + timedelta(days=365)).isoformat(),
        can_schedule=application["application_status"] == "Shortlisted",
    )


@interviews_bp.post("/employer/interviews/<int:interview_id>/cancel")
def cancel(interview_id: int):
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        flash("Please log in as an employer first.", "error")
        return redirect(url_for("employer.login"))

    connection = get_db_connection()
    result = cancel_interview(
        connection,
        employer_id,
        interview_id,
        request.form.get("reason", "").strip(),
    )
    connection.close()
    flash(result.message, "success" if result.succeeded else "error")
    return redirect(url_for("interviews.employer_interviews"))


@interviews_bp.post("/employer/interviews/<int:interview_id>/complete")
def complete(interview_id: int):
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        flash("Please log in as an employer first.", "error")
        return redirect(url_for("employer.login"))

    connection = get_db_connection()
    result = complete_interview(connection, employer_id, interview_id)
    connection.close()
    flash(result.message, "success" if result.succeeded else "error")
    return redirect(url_for("interviews.employer_interviews"))


def _interview_form_details() -> InterviewDetails:
    return InterviewDetails(
        scheduled_date=request.form.get("scheduled_date", "").strip(),
        scheduled_time=request.form.get("scheduled_time", "").strip(),
        duration_minutes=request.form.get("duration_minutes", "").strip(),
        interview_mode=request.form.get("interview_mode", "").strip(),
        location_or_link=request.form.get("location_or_link", "").strip(),
        notes=request.form.get("notes", "").strip(),
    )


def _interview_form_defaults(interview: dict | None) -> dict[str, str]:
    if interview:
        scheduled_date, scheduled_time = interview["scheduled_input"].split(
            "T",
            1,
        )
        return {
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
            "duration_minutes": str(interview["duration_minutes"]),
            "interview_mode": str(interview["interview_mode"]),
            "location_or_link": str(interview["location_or_link"]),
            "notes": str(interview.get("notes") or ""),
        }

    default_time = datetime.now(MALAYSIA_TIMEZONE) + timedelta(days=1)
    default_time = default_time.replace(hour=10, minute=0, second=0)
    return {
        "scheduled_date": default_time.strftime("%Y-%m-%d"),
        "scheduled_time": default_time.strftime("%H:%M"),
        "duration_minutes": "60",
        "interview_mode": "Online",
        "location_or_link": "",
        "notes": "",
    }


def _logged_in_seeker_id() -> int | None:
    seeker_id = session.get("seeker_id")

    if seeker_id is None or session.get("seeker_authenticated") is not True:
        return None

    return int(seeker_id)


def _logged_in_employer_id() -> int | None:
    employer_id = session.get("employer_id")
    return int(employer_id) if employer_id is not None else None
