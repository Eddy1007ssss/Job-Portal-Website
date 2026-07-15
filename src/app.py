import os
import re
import sqlite3

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_FOLDER = os.path.join(
    BASE_DIR,
    "templates"
)

STATIC_FOLDER = os.path.join(
    BASE_DIR,
    "static"
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "jobportal.db"
)


# ---------------------------------------------------------
# Flask application
# ---------------------------------------------------------

app = Flask(
    __name__,
    template_folder=TEMPLATE_FOLDER,
    static_folder=STATIC_FOLDER,
    static_url_path="/static"
)

app.secret_key = "job-portal-development-secret-key"

# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "jobportal.db"
)


def get_db_connection():
    """
    Create and return a connection to the SQLite database.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def init_database():
    """
    Create all required database tables if they do not exist.
    """

    connection = get_db_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employers (
            employer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            company_email TEXT NOT NULL UNIQUE,
            contact_number TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS company_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_id INTEGER NOT NULL UNIQUE,
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            address TEXT NOT NULL,
            company_description TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            contact_number TEXT NOT NULL,
            website TEXT,
            company_size TEXT,
            logo_url TEXT,
            banner_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (employer_id)
                REFERENCES employers(employer_id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()
    connection.close()


# ---------------------------------------------------------
# General routes
# ---------------------------------------------------------

@app.route("/health")
def health():
    return {
        "status": "ok"
    }


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/seeker-profile")
def seeker_profile():
    return render_template("seeker_profile.html")

@app.route("/seeker/login")
def seeker_login():
    return redirect(
        url_for("seeker_profile")
    )


@app.route("/seeker/register")
def seeker_register():
    return redirect(
        url_for("seeker_profile")
    )


@app.route("/jobs")
def job_listings():
    return "<h1>Job Listings</h1>"


@app.route("/companies")
def companies():
    return render_template("companies.html")


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
    session.clear()

    flash(
        "You have logged out successfully.",
        "success"
    )

    return redirect(url_for("home"))


# ---------------------------------------------------------
# Employer registration
# User Story 1
# ---------------------------------------------------------

@app.route(
    "/employer/register",
    methods=["GET", "POST"]
)
def employer_register():

    if request.method == "POST":

        company_name = request.form.get(
            "company_name",
            ""
        ).strip()

        company_email = request.form.get(
            "company_email",
            ""
        ).strip().lower()

        contact_number = request.form.get(
            "contact_number",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        errors = []

        # Company name validation
        if not company_name:
            errors.append(
                "Company name is required."
            )

        elif len(company_name) < 2:
            errors.append(
                "Company name must contain at least 2 characters."
            )

        # Email validation
        email_pattern = (
            r"^[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        )

        if not company_email:
            errors.append(
                "Company email is required."
            )

        elif not re.match(
            email_pattern,
            company_email
        ):
            errors.append(
                "Please enter a valid company email."
            )

        # Contact number validation
        phone_pattern = r"^[0-9+\-\s]{8,15}$"

        if not contact_number:
            errors.append(
                "Contact number is required."
            )

        elif not re.match(
            phone_pattern,
            contact_number
        ):
            errors.append(
                "Contact number must contain between "
                "8 and 15 numbers."
            )

        # Password validation
        if not password:
            errors.append(
                "Password is required."
            )

        elif len(password) < 8:
            errors.append(
                "Password must contain at least 8 characters."
            )

        if password != confirm_password:
            errors.append(
                "Passwords do not match."
            )

        connection = get_db_connection()

        existing_employer = connection.execute(
            """
            SELECT employer_id
            FROM employers
            WHERE company_email = ?
            """,
            (company_email,)
        ).fetchone()

        if existing_employer:
            errors.append(
                "This company email is already registered."
            )

        if errors:
            connection.close()

            for error in errors:
                flash(
                    error,
                    "error"
                )

            return render_template(
                "employer_register.html",
                company_name=company_name,
                company_email=company_email,
                contact_number=contact_number
            )

        password_hash = generate_password_hash(
            password
        )

        cursor = connection.execute(
            """
            INSERT INTO employers (
                company_name,
                company_email,
                contact_number,
                password_hash
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                company_name,
                company_email,
                contact_number,
                password_hash
            )
        )

        employer_id = cursor.lastrowid

        connection.commit()
        connection.close()

        session.clear()

        session["employer_id"] = employer_id
        session["employer_company_name"] = company_name
        session["employer_email"] = company_email

        flash(
            "Employer account created successfully. "
            "Please complete your company profile.",
            "success"
        )

        return redirect(
            url_for("employer_company_profile")
        )

    return render_template(
        "employer_register.html"
    )


# ---------------------------------------------------------
# Employer login
# ---------------------------------------------------------

@app.route(
    "/employer/login",
    methods=["GET", "POST"]
)
def employer_login():

    if request.method == "POST":

        company_email = request.form.get(
            "company_email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not company_email or not password:
            flash(
                "Please enter your email and password.",
                "error"
            )

            return render_template(
                "employer_login.html"
            )

        connection = get_db_connection()

        employer = connection.execute(
            """
            SELECT *
            FROM employers
            WHERE company_email = ?
            """,
            (company_email,)
        ).fetchone()

        connection.close()

        if employer is None:
            flash(
                "Employer account was not found.",
                "error"
            )

            return render_template(
                "employer_login.html"
            )

        password_is_correct = check_password_hash(
            employer["password_hash"],
            password
        )

        if not password_is_correct:
            flash(
                "Incorrect password.",
                "error"
            )

            return render_template(
                "employer_login.html"
            )

        session.clear()

        session["employer_id"] = employer["employer_id"]

        session["employer_company_name"] = (
            employer["company_name"]
        )

        session["employer_email"] = (
            employer["company_email"]
        )

        flash(
            "Login successful.",
            "success"
        )

        return redirect(
            url_for("employer_company_profile")
        )

    return render_template(
        "employer_login.html"
    )


# ---------------------------------------------------------
# Employer logout
# ---------------------------------------------------------

@app.route("/employer/logout")
def employer_logout():

    session.clear()

    flash(
        "You have logged out successfully.",
        "success"
    )

    return redirect(
        url_for("employer_login")
    )


# ---------------------------------------------------------
# Create or edit company profile
# User Story 2
# ---------------------------------------------------------

@app.route(
    "/employer/company-profile",
    methods=["GET", "POST"]
)
def employer_company_profile():

    employer_id = session.get(
        "employer_id"
    )

    if employer_id is None:
        flash(
            "Please log in as an employer first.",
            "error"
        )

        return redirect(
            url_for("employer_login")
        )

    connection = get_db_connection()

    employer = connection.execute(
        """
        SELECT *
        FROM employers
        WHERE employer_id = ?
        """,
        (employer_id,)
    ).fetchone()

    if employer is None:
        connection.close()

        session.clear()

        flash(
            "Employer account was not found.",
            "error"
        )

        return redirect(
            url_for("employer_login")
        )

    existing_profile = connection.execute(
        """
        SELECT *
        FROM company_profiles
        WHERE employer_id = ?
        """,
        (employer_id,)
    ).fetchone()

    if request.method == "POST":

        company_name = request.form.get(
            "company_name",
            ""
        ).strip()

        industry = request.form.get(
            "industry",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        company_description = request.form.get(
            "company_description",
            ""
        ).strip()

        contact_email = request.form.get(
            "contact_email",
            ""
        ).strip().lower()

        contact_number = request.form.get(
            "contact_number",
            ""
        ).strip()

        website = request.form.get(
            "website",
            ""
        ).strip()

        company_size = request.form.get(
            "company_size",
            ""
        ).strip()

        logo_url = request.form.get(
            "logo_url",
            ""
        ).strip()

        banner_url = request.form.get(
            "banner_url",
            ""
        ).strip()

        errors = []

        if not company_name:
            errors.append(
                "Company name is required."
            )

        if not industry:
            errors.append(
                "Industry is required."
            )

        if not address:
            errors.append(
                "Company address is required."
            )

        if not company_description:
            errors.append(
                "Company description is required."
            )

        elif len(company_description) < 30:
            errors.append(
                "Company description must contain "
                "at least 30 characters."
            )

        email_pattern = (
            r"^[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        )

        if not contact_email:
            errors.append(
                "Contact email is required."
            )

        elif not re.match(
            email_pattern,
            contact_email
        ):
            errors.append(
                "Please enter a valid contact email."
            )

        phone_pattern = r"^[0-9+\-\s]{8,15}$"

        if not contact_number:
            errors.append(
                "Contact number is required."
            )

        elif not re.match(
            phone_pattern,
            contact_number
        ):
            errors.append(
                "Contact number must contain between "
                "8 and 15 numbers."
            )

        if errors:
            connection.close()

            for error in errors:
                flash(
                    error,
                    "error"
                )

            submitted_profile = {
                "company_name": company_name,
                "industry": industry,
                "address": address,
                "company_description": company_description,
                "contact_email": contact_email,
                "contact_number": contact_number,
                "website": website,
                "company_size": company_size,
                "logo_url": logo_url,
                "banner_url": banner_url
            }

            return render_template(
                "employer_company_profile.html",
                employer=employer,
                profile=submitted_profile
            )

        if existing_profile:

            connection.execute(
                """
                UPDATE company_profiles
                SET
                    company_name = ?,
                    industry = ?,
                    address = ?,
                    company_description = ?,
                    contact_email = ?,
                    contact_number = ?,
                    website = ?,
                    company_size = ?,
                    logo_url = ?,
                    banner_url = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE employer_id = ?
                """,
                (
                    company_name,
                    industry,
                    address,
                    company_description,
                    contact_email,
                    contact_number,
                    website,
                    company_size,
                    logo_url,
                    banner_url,
                    employer_id
                )
            )

            success_message = (
                "Company profile updated successfully."
            )

        else:

            connection.execute(
                """
                INSERT INTO company_profiles (
                    employer_id,
                    company_name,
                    industry,
                    address,
                    company_description,
                    contact_email,
                    contact_number,
                    website,
                    company_size,
                    logo_url,
                    banner_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    employer_id,
                    company_name,
                    industry,
                    address,
                    company_description,
                    contact_email,
                    contact_number,
                    website,
                    company_size,
                    logo_url,
                    banner_url
                )
            )

            success_message = (
                "Company profile created successfully."
            )

        connection.execute(
            """
            UPDATE employers
            SET
                company_name = ?,
                contact_number = ?
            WHERE employer_id = ?
            """,
            (
                company_name,
                contact_number,
                employer_id
            )
        )

        connection.commit()
        connection.close()

        session["employer_company_name"] = company_name

        flash(
            success_message,
            "success"
        )

        return redirect(
            url_for("employer_company_preview")
        )

    connection.close()

    return render_template(
        "employer_company_profile.html",
        employer=employer,
        profile=existing_profile
    )


# ---------------------------------------------------------
# Employer company profile preview
# User Story 3
# ---------------------------------------------------------

@app.route(
    "/employer/company-profile/preview"
)
def employer_company_preview():

    employer_id = session.get(
        "employer_id"
    )

    if employer_id is None:
        flash(
            "Please log in as an employer first.",
            "error"
        )

        return redirect(
            url_for("employer_login")
        )

    connection = get_db_connection()

    profile = connection.execute(
        """
        SELECT
            company_profiles.*,
            employers.company_email
        FROM company_profiles

        JOIN employers
            ON company_profiles.employer_id =
               employers.employer_id

        WHERE company_profiles.employer_id = ?
        """,
        (employer_id,)
    ).fetchone()

    connection.close()

    if profile is None:
        flash(
            "Please create your company profile "
            "before previewing it.",
            "error"
        )

        return redirect(
            url_for("employer_company_profile")
        )

    return render_template(
        "company_profile.html",
        company=profile,
        preview_mode=True
    )


# ---------------------------------------------------------
# Public company profile displayed to job seekers
# ---------------------------------------------------------

@app.route(
    "/companies/<int:employer_id>"
)
def public_company_profile(
    employer_id
):

    connection = get_db_connection()

    profile = connection.execute(
        """
        SELECT
            company_profiles.*,
            employers.company_email
        FROM company_profiles

        JOIN employers
            ON company_profiles.employer_id =
               employers.employer_id

        WHERE company_profiles.employer_id = ?
        """,
        (employer_id,)
    ).fetchone()

    connection.close()

    if profile is None:
        return render_template(
            "error.html"
        ), 404

    return render_template(
        "company_profile.html",
        company=profile,
        preview_mode=False
    )


# ---------------------------------------------------------
# Error handling
# ---------------------------------------------------------

@app.errorhandler(404)
def page_not_found(
    error
):
    return render_template(
        "error.html"
    ), 404


# ---------------------------------------------------------
# Run Flask application
# ---------------------------------------------------------

if __name__ == "__main__":
    init_database()

    print("=" * 60)
    print("App file:", os.path.abspath(__file__))
    print("Base directory:", BASE_DIR)
    print("Static folder:", app.static_folder)
    print("Template folder:", app.template_folder)
    print("Home template exists:", os.path.exists(
        os.path.join(app.template_folder, "home.html")
    ))
    print("Database:", DATABASE_PATH)
    print("=" * 60)
    print(app.url_map)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )