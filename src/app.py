from flask import Flask, render_template, redirect, url_for

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static"
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


@app.route("/logout")
def logout():
    return redirect(url_for("home"))


if __name__ == "__main__":
    print("Static folder:", app.static_folder)
    print("Template folder:", app.template_folder)
    print(app.url_map)

    app.run(debug=True)