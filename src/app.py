from pathlib import Path

from flask import Flask, redirect, render_template, url_for

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
    static_url_path="/static",
)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/seeker-profile")
def seeker_profile():
    return render_template("seeker_profile.html")


@app.route("/jobs")
def job_listings():
    return "<h1>Job Listings</h1>"


@app.route("/companies")
def companies():
    return "<h1>Companies</h1>"


@app.route("/career-tips")
def career_tips():
    return "<h1>Career Tips</h1>"


@app.route("/about")
def about():
    return "<h1>About Us</h1>"


@app.route("/applications")
def applications():
    return "<h1>My Applications</h1>"


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


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/logout")
def logout():
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
