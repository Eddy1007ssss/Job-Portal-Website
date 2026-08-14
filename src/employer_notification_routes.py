from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from src.database import get_db_connection
from src.employer_notifications import (
    get_employer_notification_summary,
    get_employer_notification_target,
    get_employer_notifications,
    mark_all_employer_notifications_read,
    mark_employer_notification_read,
    normalise_notification_filter,
    sync_employer_notifications,
)

employer_notifications_bp = Blueprint(
    "employer_notifications",
    __name__,
)


@employer_notifications_bp.get("/employer/notifications")
def notification_list():
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        return _login_redirect()

    selected_filter = normalise_notification_filter(
        request.args.get("filter"),
    )
    connection = get_db_connection()
    sync_employer_notifications(connection, employer_id)
    notifications = get_employer_notifications(
        connection,
        employer_id,
        selected_filter,
    )
    summary = get_employer_notification_summary(connection, employer_id)
    connection.close()
    return render_template(
        "employer_notifications.html",
        notifications=notifications,
        summary=summary,
        selected_filter=selected_filter,
    )


@employer_notifications_bp.post("/employer/notifications/read-all")
def read_all_notifications():
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        return _login_redirect()

    connection = get_db_connection()
    updated_count = mark_all_employer_notifications_read(
        connection,
        employer_id,
    )
    connection.close()
    message = (
        f"Marked {updated_count} notification"
        f"{'s' if updated_count != 1 else ''} as read."
        if updated_count
        else "You have no unread notifications."
    )
    flash(message, "success")
    return redirect(url_for("employer_notifications.notification_list"))


@employer_notifications_bp.post("/employer/notifications/<int:notification_id>/read")
def read_notification(notification_id: int):
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        return _login_redirect()

    connection = get_db_connection()
    updated = mark_employer_notification_read(
        connection,
        employer_id,
        notification_id,
    )
    connection.close()

    if not updated:
        flash("Notification was not found.", "error")

    return redirect(url_for("employer_notifications.notification_list"))


@employer_notifications_bp.post("/employer/notifications/<int:notification_id>/open")
def open_notification(notification_id: int):
    employer_id = _logged_in_employer_id()

    if employer_id is None:
        return _login_redirect()

    connection = get_db_connection()
    target = get_employer_notification_target(
        connection,
        employer_id,
        notification_id,
    )

    if target is not None:
        mark_employer_notification_read(
            connection,
            employer_id,
            notification_id,
        )

    connection.close()

    if target is None or target.get("application_id") is None:
        flash("Notification details were not found.", "error")
        return redirect(url_for("employer_notifications.notification_list"))

    application_id = int(target["application_id"])

    if str(target["notification_type"]).startswith("interview_"):
        return redirect(
            url_for(
                "interviews.manage_interview",
                application_id=application_id,
            )
        )

    return redirect(
        url_for(
            "employer_applications.application_details",
            application_id=application_id,
        )
    )


def _logged_in_employer_id() -> int | None:
    employer_id = session.get("employer_id")
    return int(employer_id) if employer_id is not None else None


def _login_redirect():
    flash("Please log in as an employer first.", "error")
    return redirect(url_for("employer.login"))
