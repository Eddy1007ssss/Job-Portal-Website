import os

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from src.admin import admin_bp
from src.applications import applications_bp
from src.database import get_db_connection, init_database
from src.employer import employer_bp
from src.employer_applications import employer_applications_bp
from src.employer_dashboard import employer_dashboard_bp
from src.employer_notification_routes import employer_notifications_bp
from src.employer_notifications import (
    get_unread_employer_notification_count,
    sync_employer_notifications,
)
from src.interview_management import get_pending_interview_count
from src.interviews import interviews_bp
from src.jobs import jobs_bp
from src.password_reset import password_reset_bp
from src.portal_pages import (
    PROFILE_VISIBILITY_OPTIONS,
    get_companies,
    get_job_notifications,
    get_notification_job_id,
    get_portal_stats,
    get_seeker_settings,
    get_unread_notification_count,
    mark_all_notifications_read,
    mark_notification_read,
    sync_recent_job_notifications,
    update_seeker_settings,
)
from src.seeker import seeker_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
        static_url_path="/static",
    )

    app.secret_key = os.environ.get(
        "SECRET_KEY",
        "job-portal-development-secret-key",
    )

    app.config["DATABASE_PATH"] = os.environ.get(
        "DATABASE_PATH",
        os.path.join(BASE_DIR, "jobportal.db"),
    )

    app.register_blueprint(seeker_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employer_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(employer_applications_bp)
    app.register_blueprint(employer_dashboard_bp)
    app.register_blueprint(employer_notifications_bp)
    app.register_blueprint(interviews_bp)
    app.register_blueprint(password_reset_bp)

    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "1") == "1"
    app.config["MAIL_USE_SSL"] = os.environ.get("MAIL_USE_SSL", "0") == "1"
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        "no-reply@jobportal.local",
    )

    init_database(app)

    return app


app = create_app()


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/companies")
def companies():
    db = get_db_connection()
    company_rows = get_companies(db)
    db.close()
    return render_template("companies.html", companies=company_rows)


@app.route("/career-tips")
def career_tips():
    return "<h1>Career Tips</h1>"


@app.route("/about")
def about():
    db = get_db_connection()
    stats = get_portal_stats(db)
    db.close()
    return render_template("about.html", stats=stats)


@app.get("/job-alerts")
def job_alerts():
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        return _seeker_login_redirect()

    db = get_db_connection()
    sync_recent_job_notifications(db, seeker_id)
    notifications = get_job_notifications(db, seeker_id)
    unread_count = get_unread_notification_count(db, seeker_id)
    db.close()
    return render_template(
        "job_alerts.html",
        notifications=notifications,
        unread_count=unread_count,
    )


@app.post("/job-alerts/read-all")
def read_all_job_notifications():
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        return _seeker_login_redirect()

    db = get_db_connection()
    updated_count = mark_all_notifications_read(db, seeker_id)
    db.close()

    if updated_count:
        flash("All new-job notifications marked as read.", "success")
    else:
        flash("You have no unread notifications.", "success")

    return redirect(url_for("job_alerts"))


@app.post("/job-alerts/<int:notification_id>/open")
def open_job_notification(notification_id: int):
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        return _seeker_login_redirect()

    db = get_db_connection()
    job_id = get_notification_job_id(db, seeker_id, notification_id)

    if job_id is not None:
        mark_notification_read(db, seeker_id, notification_id)

    db.close()

    if job_id is None:
        flash("Job notification was not found.", "error")
        return redirect(url_for("job_alerts"))

    return redirect(url_for("jobs.job_details", job_id=job_id))


@app.route("/resume")
def resume():
    return "<h1>Resume</h1>"


@app.get("/settings")
def settings():
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        return _seeker_login_redirect()

    db = get_db_connection()
    seeker_settings = get_seeker_settings(db, seeker_id)
    db.close()
    return render_template(
        "settings.html",
        settings=seeker_settings,
        visibility_options=PROFILE_VISIBILITY_OPTIONS,
    )


@app.post("/settings/preferences")
def update_settings_preferences():
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        return _seeker_login_redirect()

    db = get_db_connection()
    result = update_seeker_settings(
        db,
        seeker_id,
        email_notifications=request.form.get("email_notifications") == "on",
        application_updates=request.form.get("application_updates") == "on",
        job_recommendations=request.form.get("job_recommendations") == "on",
        profile_visibility=request.form.get(
            "profile_visibility",
            "Employers",
        ),
    )
    db.close()

    if result.succeeded:
        flash("Preferences updated successfully.", "success")
    else:
        flash("Select a valid profile visibility option.", "error")

    return redirect(url_for("settings"))


@app.post("/settings/password")
def update_settings_password():
    seeker_id = _logged_in_seeker_id()

    if seeker_id is None:
        return _seeker_login_redirect()

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    db = get_db_connection()
    seeker = db.execute(
        "SELECT password_hash FROM seekers WHERE seeker_id = ?",
        (seeker_id,),
    ).fetchone()

    if seeker is None or not check_password_hash(
        seeker["password_hash"],
        current_password,
    ):
        db.close()
        flash("Current password is incorrect.", "error")
        return redirect(url_for("settings"))

    if len(new_password) < 8:
        db.close()
        flash("New password must contain at least 8 characters.", "error")
        return redirect(url_for("settings"))

    if new_password != confirm_password:
        db.close()
        flash("New passwords do not match.", "error")
        return redirect(url_for("settings"))

    if check_password_hash(seeker["password_hash"], new_password):
        db.close()
        flash("Choose a password different from your current password.", "error")
        return redirect(url_for("settings"))

    db.execute(
        "UPDATE seekers SET password_hash = ? WHERE seeker_id = ?",
        (generate_password_hash(new_password), seeker_id),
    )
    db.commit()
    db.close()
    flash("Password changed successfully.", "success")
    return redirect(url_for("settings"))


@app.route("/register")
def register():
    return "<h1>Register</h1>"


@app.context_processor
def inject_notification_count() -> dict[str, int]:
    seeker_id = _logged_in_seeker_id()
    employer_id = _logged_in_employer_id()
    notification_count = 0
    interview_invitation_count = 0
    employer_notification_count = 0

    if seeker_id is not None:
        db = get_db_connection()
        notification_count = get_unread_notification_count(db, seeker_id)
        interview_invitation_count = get_pending_interview_count(db, seeker_id)
        db.close()

    if employer_id is not None:
        db = get_db_connection()
        sync_employer_notifications(db, employer_id)
        employer_notification_count = get_unread_employer_notification_count(
            db, employer_id
        )
        db.close()

    return {
        "notification_count": notification_count,
        "interview_invitation_count": interview_invitation_count,
        "employer_notification_count": employer_notification_count,
    }


def _logged_in_seeker_id() -> int | None:
    seeker_id = session.get("seeker_id")

    if seeker_id is None or session.get("seeker_authenticated") is not True:
        return None

    return int(seeker_id)


def _logged_in_employer_id() -> int | None:
    employer_id = session.get("employer_id")
    return int(employer_id) if employer_id is not None else None


def _seeker_login_redirect():
    flash("Please log in as a job seeker first.", "error")
    return redirect(url_for("seeker.login"))


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=8000,
    )
