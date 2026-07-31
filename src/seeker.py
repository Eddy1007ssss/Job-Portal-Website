import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from src.database import get_db_connection

seeker_bp = Blueprint("seeker", __name__)
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
RESUME_EXTENSIONS = {"pdf"}
CERTIFICATE_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_PATTERN = re.compile(r"^[0-9+\-\s]{8,15}$")


def _clear_seeker_session() -> None:
    session.pop("seeker_id", None)
    session.pop("seeker_name", None)
    session.pop("seeker_email", None)
    session.pop("seeker_authenticated", None)


@seeker_bp.before_request
def require_seeker_login():
    """Protect every seeker route except registration, login and logout."""

    public_endpoints = {
        "seeker.register",
        "seeker.login",
        "seeker.logout",
    }

    if request.endpoint in public_endpoints:
        return None

    if (
        session.get("seeker_id") is None
        or session.get("seeker_authenticated") is not True
    ):
        _clear_seeker_session()
        flash("Please log in as a job seeker first.", "error")
        return redirect(url_for("seeker.login"))

    return None


def _allowed(filename: str, extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def _is_pdf(file) -> bool:
    """Confirm that an uploaded file has a real PDF signature."""

    original_position = file.stream.tell()
    signature = file.stream.read(5)
    file.stream.seek(original_position)

    return signature == b"%PDF-"


def _folder(name: str) -> Path:
    static_folder = current_app.static_folder
    if static_folder is None:
        raise RuntimeError("Flask static folder is not configured.")

    path = Path(static_folder) / "uploads" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate_month_range(
    start_value: str,
    end_value: str,
) -> str | None:
    """Validate YYYY-MM month values used by experience forms."""

    if not start_value:
        return "Start date is required."

    if end_value and end_value != "Present" and end_value < start_value:
        return "End date cannot be earlier than the start date."

    return None


def _validate_issue_month(issue_date: str) -> str | None:
    """Reject certificate issue dates that are in the future."""

    if not issue_date:
        return None

    current_month = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m")

    if issue_date > current_month:
        return "Certificate issue date cannot be in the future."

    return None


def _parse_month(value: str) -> date | None:
    """Convert an HTML month value (YYYY-MM) into a date."""

    if not value:
        return None

    try:
        year_text, month_text = value.split("-", 1)
        return date(int(year_text), int(month_text), 1)
    except TypeError, ValueError:
        return None


def _validate_date_range(
    start_value: str,
    end_value: str,
) -> str | None:
    start_date = _parse_month(start_value)
    end_date = _parse_month(end_value)
    current_month = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).date().replace(day=1)

    if not start_date:
        return "Please enter a valid start date."

    if start_date > current_month:
        return "The start date cannot be in the future."

    if end_value and not end_date:
        return "Please enter a valid end date."

    if end_date and end_date > current_month:
        return "The end date cannot be in the future."

    if end_date and end_date < start_date:
        return "The end date cannot be earlier than the start date."

    return None


def ensure_demo_seeker() -> int:
    db = get_db_connection()
    row = db.execute(
        "SELECT seeker_id FROM seekers WHERE email = ?",
        ("johndoe@email.com",),
    ).fetchone()

    if row:
        seeker_id = int(row["seeker_id"])
        db.close()
        return seeker_id

    cursor = db.execute(
        """
        INSERT INTO seekers (full_name, email, contact_number, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        (
            "John Doe",
            "johndoe@email.com",
            "+60 12-345 6789",
            generate_password_hash("Password123"),
        ),
    )
    inserted_seeker_id = cursor.lastrowid
    if inserted_seeker_id is None:
        db.close()
        raise RuntimeError("Failed to create the demo seeker account.")

    seeker_id = int(inserted_seeker_id)

    db.execute(
        """
        INSERT INTO seeker_profiles (
            seeker_id, job_title, location, about_me, job_categories,
            employment_type, preferred_location, expected_salary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            seeker_id,
            "UI/UX Designer",
            "Kuala Lumpur, Malaysia",
            "Creative and detail-oriented UI/UX Designer.",
            "UI/UX Design, Product Design",
            "Full-time",
            "Kuala Lumpur, Selangor",
            "RM 4,000 - RM 6,000",
        ),
    )

    db.execute(
        """
        INSERT INTO seeker_experiences (
            seeker_id, position_title, company_name, start_date, end_date, description
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            seeker_id,
            "UI/UX Designer",
            "ABC Digital Sdn. Bhd.",
            "January 2022",
            "Present",
            "Designed web and mobile interfaces.",
        ),
    )

    db.execute(
        """
        INSERT INTO seeker_education (
            seeker_id, qualification, institution, start_year, end_year, status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            seeker_id,
            "Bachelor of Multimedia Design",
            "TAR UMT",
            "2016",
            "2020",
            "Completed",
        ),
    )

    for skill in ["UI Design", "UX Research", "Figma", "Adobe XD"]:
        db.execute(
            "INSERT OR IGNORE INTO seeker_skills (seeker_id, skill_name) VALUES (?, ?)",
            (seeker_id, skill),
        )

    db.execute(
        """
        INSERT INTO seeker_certificates (
            seeker_id, certificate_name, issuer, issue_date
        )
        VALUES (?, ?, ?, ?)
        """,
        (seeker_id, "Google UX Design Certificate", "Google", "September 2023"),
    )

    for language, level in [
        ("English", "Fluent"),
        ("Malay", "Native"),
        ("Chinese", "Intermediate"),
    ]:
        db.execute(
            """
            INSERT OR IGNORE INTO seeker_languages (
                seeker_id, language_name, proficiency
            )
            VALUES (?, ?, ?)
            """,
            (seeker_id, language, level),
        )

    db.commit()
    db.close()
    return seeker_id


def current_seeker_id() -> int:
    seeker_id = session.get("seeker_id")

    if seeker_id is None:
        raise RuntimeError("A seeker login is required.")

    return int(seeker_id)


def load_profile(seeker_id: int) -> dict | None:
    db = get_db_connection()
    row = db.execute(
        """
        SELECT seekers.*, seeker_profiles.*
        FROM seekers
        LEFT JOIN seeker_profiles
            ON seekers.seeker_id = seeker_profiles.seeker_id
        WHERE seekers.seeker_id = ?
        """,
        (seeker_id,),
    ).fetchone()

    if row is None:
        db.close()
        return None

    profile = dict(row)
    profile["experiences"] = db.execute(
        "SELECT * FROM seeker_experiences WHERE seeker_id = ? ORDER BY experience_id DESC",
        (seeker_id,),
    ).fetchall()
    profile["education_items"] = db.execute(
        "SELECT * FROM seeker_education WHERE seeker_id = ? ORDER BY education_id DESC",
        (seeker_id,),
    ).fetchall()
    profile["skills"] = db.execute(
        "SELECT * FROM seeker_skills WHERE seeker_id = ? ORDER BY skill_name",
        (seeker_id,),
    ).fetchall()
    profile["certificates"] = db.execute(
        "SELECT * FROM seeker_certificates WHERE seeker_id = ? ORDER BY certificate_id DESC",
        (seeker_id,),
    ).fetchall()
    profile["languages"] = db.execute(
        "SELECT * FROM seeker_languages WHERE seeker_id = ? ORDER BY language_name",
        (seeker_id,),
    ).fetchall()
    db.close()
    return profile


@seeker_bp.route(
    "/seeker/register",
    methods=["GET", "POST"],
)
def register():
    """Register and sign in a new job seeker."""

    if session.get("seeker_id") is not None:
        return redirect(url_for("jobs.list_jobs"))

    if request.method == "GET":
        return render_template("seeker_register.html")

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    contact_number = request.form.get("contact_number", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    errors = []

    if len(full_name) < 2:
        errors.append("Full name must contain at least 2 characters.")

    if not EMAIL_PATTERN.fullmatch(email):
        errors.append("Please enter a valid email address.")

    if not PHONE_PATTERN.fullmatch(contact_number):
        errors.append(
            "Phone number must contain between 8 and 15 characters "
            "and may include numbers, spaces, + or -."
        )

    if len(password) < 8:
        errors.append("Password must contain at least 8 characters.")

    if password != confirm_password:
        errors.append("Passwords do not match.")

    db = get_db_connection()
    existing_seeker = db.execute(
        "SELECT seeker_id FROM seekers WHERE email = ?",
        (email,),
    ).fetchone()

    if existing_seeker is not None:
        errors.append("This email address is already registered.")

    if errors:
        db.close()

        for error in errors:
            flash(error, "error")

        return render_template(
            "seeker_register.html",
            full_name=full_name,
            email=email,
            contact_number=contact_number,
        )

    try:
        cursor = db.execute(
            """
            INSERT INTO seekers (
                full_name,
                email,
                contact_number,
                password_hash
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                full_name,
                email,
                contact_number,
                generate_password_hash(password),
            ),
        )
        seeker_id = int(cursor.lastrowid)
        db.execute(
            "INSERT INTO seeker_profiles (seeker_id) VALUES (?)",
            (seeker_id,),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        db.close()
        flash("This email address is already registered.", "error")
        return render_template(
            "seeker_register.html",
            full_name=full_name,
            email=email,
            contact_number=contact_number,
        )

    db.close()

    session.clear()
    session["seeker_id"] = seeker_id
    session["seeker_name"] = full_name
    session["seeker_email"] = email
    session["seeker_authenticated"] = True

    flash("Your job seeker account was created successfully.", "success")
    return redirect(url_for("jobs.list_jobs"))


@seeker_bp.route(
    "/seeker/login",
    methods=["GET", "POST"],
)
def login():
    """Log in a registered job seeker."""

    if session.get("seeker_id") is not None:
        return redirect(url_for("jobs.list_jobs"))

    if request.method == "GET":
        return render_template("seeker_login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    db = get_db_connection()
    seeker = db.execute(
        """
        SELECT
            seeker_id,
            full_name,
            email,
            password_hash
        FROM seekers
        WHERE email = ?
        """,
        (email,),
    ).fetchone()
    db.close()

    if seeker is None or not check_password_hash(
        seeker["password_hash"],
        password,
    ):
        flash("Incorrect email or password.", "error")
        return render_template(
            "seeker_login.html",
            email=email,
        )

    session.clear()
    session["seeker_id"] = int(seeker["seeker_id"])
    session["seeker_name"] = seeker["full_name"]
    session["seeker_email"] = seeker["email"]
    session["seeker_authenticated"] = True

    flash("Welcome back! You can now find and apply for jobs.", "success")
    return redirect(url_for("jobs.list_jobs"))


@seeker_bp.route("/seeker-profile")
def profile():
    data = load_profile(current_seeker_id())
    if data is None:
        flash("Profile not found.", "error")
        return redirect(url_for("home"))
    return render_template("seeker_profile.html", profile=data)


@seeker_bp.post("/seeker-profile/update")
def update_profile():
    seeker_id = current_seeker_id()
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not full_name or not email:
        flash("Full name and email are required.", "error")
        return redirect(url_for("seeker.profile"))

    db = get_db_connection()
    try:
        db.execute(
            """
            UPDATE seekers
            SET full_name = ?, email = ?, contact_number = ?
            WHERE seeker_id = ?
            """,
            (
                full_name,
                email,
                request.form.get("contact_number", "").strip(),
                seeker_id,
            ),
        )
        db.execute(
            """
            UPDATE seeker_profiles
            SET job_title = ?, location = ?, about_me = ?,
                job_categories = ?, employment_type = ?,
                preferred_location = ?, expected_salary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE seeker_id = ?
            """,
            (
                request.form.get("job_title", "").strip(),
                request.form.get("location", "").strip(),
                request.form.get("about_me", "").strip(),
                request.form.get("job_categories", "").strip(),
                request.form.get("employment_type", "").strip(),
                request.form.get("preferred_location", "").strip(),
                request.form.get("expected_salary", "").strip(),
                seeker_id,
            ),
        )
        db.commit()
        flash("Profile updated successfully.", "success")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("That email is already registered.", "error")
    finally:
        db.close()

    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/image")
def upload_image():
    seeker_id = current_seeker_id()
    file = request.files.get("profile_image")

    if not file or not file.filename or not _allowed(file.filename, IMAGE_EXTENSIONS):
        flash("Select a PNG, JPG, JPEG or WEBP image.", "error")
        return redirect(url_for("seeker.profile"))

    extension = secure_filename(file.filename).rsplit(".", 1)[1].lower()
    filename = f"seeker_{seeker_id}_{uuid4().hex}.{extension}"
    file.save(_folder("profile_images") / filename)
    relative = f"uploads/profile_images/{filename}"

    db = get_db_connection()
    old = db.execute(
        "SELECT profile_image FROM seeker_profiles WHERE seeker_id = ?",
        (seeker_id,),
    ).fetchone()
    db.execute(
        "UPDATE seeker_profiles SET profile_image = ? WHERE seeker_id = ?",
        (relative, seeker_id),
    )
    db.commit()
    db.close()

    if old and old["profile_image"]:
        old_path = Path(current_app.static_folder) / old["profile_image"]
        if old_path.exists():
            old_path.unlink()

    flash("Profile picture updated.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/resume")
def upload_resume():
    seeker_id = current_seeker_id()
    file = request.files.get("resume")

    if (
        not file
        or not file.filename
        or not _allowed(file.filename, RESUME_EXTENSIONS)
        or not _is_pdf(file)
    ):
        flash("Please select a valid PDF resume.", "error")
        return redirect(url_for("seeker.profile"))

    extension = secure_filename(file.filename).rsplit(".", 1)[1].lower()
    filename = f"seeker_{seeker_id}_{uuid4().hex}.{extension}"
    file.save(_folder("resumes") / filename)

    db = get_db_connection()
    old = db.execute(
        "SELECT resume_filename FROM seeker_profiles WHERE seeker_id = ?",
        (seeker_id,),
    ).fetchone()
    db.execute(
        "UPDATE seeker_profiles SET resume_filename = ? WHERE seeker_id = ?",
        (filename, seeker_id),
    )
    db.commit()
    db.close()

    if old and old["resume_filename"]:
        old_path = _folder("resumes") / old["resume_filename"]
        if old_path.exists():
            old_path.unlink()

    flash("Resume uploaded.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.get("/seeker-profile/resume/download")
def download_resume():
    seeker_id = current_seeker_id()
    db = get_db_connection()
    row = db.execute(
        "SELECT resume_filename FROM seeker_profiles WHERE seeker_id = ?",
        (seeker_id,),
    ).fetchone()
    db.close()

    if not row or not row["resume_filename"]:
        flash("No resume available.", "error")
        return redirect(url_for("seeker.profile"))

    return send_from_directory(
        _folder("resumes"),
        row["resume_filename"],
        as_attachment=True,
    )


@seeker_bp.post("/seeker-profile/resume/delete")
def delete_resume():
    seeker_id = current_seeker_id()
    db = get_db_connection()
    row = db.execute(
        "SELECT resume_filename FROM seeker_profiles WHERE seeker_id = ?",
        (seeker_id,),
    ).fetchone()
    db.execute(
        "UPDATE seeker_profiles SET resume_filename = NULL WHERE seeker_id = ?",
        (seeker_id,),
    )
    db.commit()
    db.close()

    if row and row["resume_filename"]:
        path = _folder("resumes") / row["resume_filename"]
        if path.exists():
            path.unlink()

    flash("Resume deleted.", "success")
    return redirect(url_for("seeker.profile"))


def _insert(table: str, columns: list[str], values: list[str]) -> None:
    db = get_db_connection()
    placeholders = ", ".join("?" for _ in values)
    db.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    db.commit()
    db.close()


def _delete(table: str, id_column: str, item_id: int) -> None:
    db = get_db_connection()
    db.execute(
        f"DELETE FROM {table} WHERE {id_column} = ? AND seeker_id = ?",
        (item_id, current_seeker_id()),
    )
    db.commit()
    db.close()


@seeker_bp.post("/seeker-profile/experience")
def add_experience():
    position = request.form.get("position_title", "").strip()
    company = request.form.get("company_name", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    currently_working = request.form.get("currently_working") == "on"

    if currently_working:
        end_date = "Present"

    if not position or not company:
        flash("Position and company are required.", "error")
        return redirect(url_for("seeker.profile"))

    date_error = _validate_month_range(start_date, end_date)

    if date_error:
        flash(date_error, "error")
        return redirect(url_for("seeker.profile"))

    _insert(
        "seeker_experiences",
        [
            "seeker_id",
            "position_title",
            "company_name",
            "start_date",
            "end_date",
            "description",
        ],
        [
            current_seeker_id(),
            position,
            company,
            start_date,
            end_date,
            request.form.get("description", "").strip(),
        ],
    )

    flash("Experience added successfully.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/experience/<int:item_id>/delete")
def delete_experience(item_id: int):
    _delete("seeker_experiences", "experience_id", item_id)
    flash("Experience deleted.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/education")
def add_education():
    qualification = request.form.get("qualification", "").strip()
    institution = request.form.get("institution", "").strip()
    if not qualification or not institution:
        flash("Qualification and institution are required.", "error")
    else:
        _insert(
            "seeker_education",
            [
                "seeker_id",
                "qualification",
                "institution",
                "start_year",
                "end_year",
                "status",
            ],
            [
                current_seeker_id(),
                qualification,
                institution,
                request.form.get("start_year", "").strip(),
                request.form.get("end_year", "").strip(),
                request.form.get("status", "Completed").strip(),
            ],
        )
        flash("Education added.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/education/<int:item_id>/delete")
def delete_education(item_id: int):
    _delete("seeker_education", "education_id", item_id)
    flash("Education deleted.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/skill")
def add_skill():
    name = request.form.get("skill_name", "").strip()
    if not name:
        flash("Skill name is required.", "error")
    else:
        try:
            _insert(
                "seeker_skills",
                ["seeker_id", "skill_name"],
                [current_seeker_id(), name],
            )
            flash("Skill added.", "success")
        except sqlite3.IntegrityError:
            flash("That skill already exists.", "error")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/skill/<int:item_id>/delete")
def delete_skill(item_id: int):
    _delete("seeker_skills", "skill_id", item_id)
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/certificate")
def add_certificate():
    certificate_name = request.form.get(
        "certificate_name",
        "",
    ).strip()
    issuer = request.form.get("issuer", "").strip()
    issue_date = request.form.get("issue_date", "").strip()
    certificate_file = request.files.get("certificate_file")

    if not certificate_name:
        flash("Certificate name is required.", "error")
        return redirect(url_for("seeker.profile"))

    date_error = _validate_issue_month(issue_date)

    if date_error:
        flash(date_error, "error")
        return redirect(url_for("seeker.profile"))

    stored_filename = None
    original_filename = None

    if certificate_file and certificate_file.filename:
        if not _allowed(
            certificate_file.filename,
            CERTIFICATE_EXTENSIONS,
        ):
            flash(
                "Certificate file must be PDF, PNG, JPG, DOC or DOCX.",
                "error",
            )
            return redirect(url_for("seeker.profile"))

        safe_name = secure_filename(certificate_file.filename)
        extension = safe_name.rsplit(".", 1)[1].lower()
        stored_filename = (
            f"certificate_{current_seeker_id()}_" f"{uuid4().hex}.{extension}"
        )
        original_filename = safe_name

        certificate_file.save(_folder("certificates") / stored_filename)

    _insert(
        "seeker_certificates",
        [
            "seeker_id",
            "certificate_name",
            "issuer",
            "issue_date",
            "certificate_filename",
            "original_filename",
        ],
        [
            current_seeker_id(),
            certificate_name,
            issuer,
            issue_date,
            stored_filename,
            original_filename,
        ],
    )

    flash("Certificate added successfully.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.get("/seeker-profile/certificate/<int:item_id>/download")
def download_certificate(item_id: int):
    db = get_db_connection()

    certificate = db.execute(
        """
        SELECT
            certificate_filename,
            original_filename
        FROM seeker_certificates
        WHERE certificate_id = ?
          AND seeker_id = ?
        """,
        (
            item_id,
            current_seeker_id(),
        ),
    ).fetchone()

    db.close()

    if certificate is None or not certificate["certificate_filename"]:
        flash(
            "No certificate file is available.",
            "error",
        )

        return redirect(url_for("seeker.profile"))

    return send_from_directory(
        _folder("certificates"),
        certificate["certificate_filename"],
        as_attachment=True,
        download_name=(
            certificate["original_filename"] or certificate["certificate_filename"]
        ),
    )


@seeker_bp.post("/seeker-profile/certificate/<int:item_id>/delete")
def delete_certificate(item_id: int):
    db = get_db_connection()
    row = db.execute(
        """
        SELECT certificate_filename
        FROM seeker_certificates
        WHERE certificate_id = ? AND seeker_id = ?
        """,
        (item_id, current_seeker_id()),
    ).fetchone()

    db.execute(
        """
        DELETE FROM seeker_certificates
        WHERE certificate_id = ? AND seeker_id = ?
        """,
        (item_id, current_seeker_id()),
    )
    db.commit()
    db.close()

    if row and row["certificate_filename"]:
        path = _folder("certificates") / row["certificate_filename"]
        if path.exists():
            path.unlink()

    flash("Certificate deleted.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/language")
def add_language():
    name = request.form.get("language_name", "").strip()
    level = request.form.get("proficiency", "").strip()
    if not name or not level:
        flash("Language and proficiency are required.", "error")
    else:
        try:
            _insert(
                "seeker_languages",
                ["seeker_id", "language_name", "proficiency"],
                [current_seeker_id(), name, level],
            )
            flash("Language added.", "success")
        except sqlite3.IntegrityError:
            flash("That language already exists.", "error")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/seeker-profile/language/<int:item_id>/delete")
def delete_language(item_id: int):
    _delete("seeker_languages", "language_id", item_id)
    flash("Language deleted.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.route("/seeker/logout")
def logout():
    _clear_seeker_session()
    flash("You have logged out successfully.", "success")
    return redirect(url_for("home"))
