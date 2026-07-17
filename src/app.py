import os

from flask import Flask, render_template
from src.applications import applications_bp
from src.database import init_database
from src.employer import employer_bp
from src.jobs import jobs_bp
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
    app.register_blueprint(employer_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(applications_bp)

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
    return render_template("companies.html")


@app.route("/career-tips")
def career_tips():
    return "<h1>Career Tips</h1>"


@app.route("/about")
def about():
    return "<h1>About Us</h1>"


@app.route("/saved-jobs")
def saved_jobs():
    return "<h1>Saved Jobs</h1>"


@app.route("/job-alerts")
def job_alerts():
    return "<h1>Job Alerts</h1>"


@app.route("/resume")
def resume():
    return "<h1>Resume</h1>"


@app.route("/settings")
def settings():
    return "<h1>Settings</h1>"


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=8000,
    )
