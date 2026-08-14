import math
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar, cast

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
from flask.typing import ResponseReturnValue
from werkzeug.security import check_password_hash, generate_password_hash

from src.database import get_db_connection

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ACCOUNT_TYPES = {"all", "seeker", "employer"}
ADMIN_ROLES = {"admin", "super_admin"}
USERS_PER_PAGE = 10
JOBS_PER_PAGE = 10
JOB_STATUS_FILTERS = {"all", "open", "closed", "draft", "removed"}

ViewFunction = TypeVar("ViewFunction", bound=Callable[..., Any])


@dataclass(frozen=True)
class UserListPage:
    users: list[sqlite3.Row]
    page: int
    per_page: int
    total_users: int
    total_pages: int

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


@dataclass(frozen=True)
class JobModerationPage:
    jobs: list[sqlite3.Row]
    page: int
    per_page: int
    total_jobs: int
    total_pages: int

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def admin_login_required(view: ViewFunction) -> ViewFunction:
    @wraps(view)
    def wrapped_view(*args: Any, **kwargs: Any) -> Any:
        if (
            session.get("admin_authenticated") is not True
            or session.get("admin_id") is None
        ):
            flash("Please log in as an administrator first.", "error")
            return redirect(url_for("admin.login"))

        return view(*args, **kwargs)

    return cast(ViewFunction, wrapped_view)


def super_admin_required(view: ViewFunction) -> ViewFunction:
    @wraps(view)
    def wrapped_view(*args: Any, **kwargs: Any) -> Any:
        if session.get("admin_role") != "super_admin":
            abort(403)

        return view(*args, **kwargs)

    return cast(ViewFunction, wrapped_view)


@admin_bp.before_app_request
def enforce_active_registered_account() -> ResponseReturnValue | None:
    """End an existing user session as soon as its account is deactivated."""

    if (
        session.get("admin_authenticated") is True
        and session.get("admin_id") is not None
    ):
        connection = get_db_connection()
        admin = connection.execute(
            """
            SELECT full_name, email, role, is_active
            FROM admins
            WHERE admin_id = ?
            """,
            (session.get("admin_id"),),
        ).fetchone()
        connection.close()

        if admin is None or not bool(admin["is_active"]):
            session.clear()
            flash(
                "Your administrator account has been deactivated.",
                "error",
            )
            return redirect(url_for("admin.login"))

        session["admin_name"] = admin["full_name"]
        session["admin_email"] = admin["email"]
        session["admin_role"] = admin["role"]
        return None

    account_type: str | None = None
    account_id: object | None = None

    if (
        session.get("seeker_authenticated") is True
        and session.get("seeker_id") is not None
    ):
        account_type = "seeker"
        account_id = session.get("seeker_id")
    elif session.get("employer_id") is not None:
        account_type = "employer"
        account_id = session.get("employer_id")

    if account_type is None or account_id is None:
        return None

    table_name = "seekers" if account_type == "seeker" else "employers"
    id_column = "seeker_id" if account_type == "seeker" else "employer_id"
    connection = get_db_connection()
    account = connection.execute(
        f"SELECT is_active FROM {table_name} WHERE {id_column} = ?",
        (account_id,),
    ).fetchone()
    connection.close()

    if account is not None and bool(account["is_active"]):
        return None

    session.clear()
    flash(
        "Your account has been deactivated. Please contact an administrator.",
        "error",
    )
    login_endpoint = "seeker.login" if account_type == "seeker" else "employer.login"
    return redirect(url_for(login_endpoint))


def count_admins(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) AS total FROM admins").fetchone()
    return int(row["total"]) if row is not None else 0


def get_administrators(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute("""
        SELECT admin_id, full_name, email, role, is_active, created_at
        FROM admins
        ORDER BY
            CASE role WHEN 'super_admin' THEN 0 ELSE 1 END,
            datetime(created_at),
            admin_id
        """).fetchall()


def get_admin_totals(connection: sqlite3.Connection) -> dict[str, int]:
    row = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN role = 'super_admin' THEN 1 ELSE 0 END) AS super_admins
        FROM admins
        """).fetchone()

    if row is None:
        return {"total": 0, "active": 0, "super_admins": 0}

    return {
        "total": int(row["total"] or 0),
        "active": int(row["active"] or 0),
        "super_admins": int(row["super_admins"] or 0),
    }


def get_job_moderation_totals(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    row = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN LOWER(status) = 'open' THEN 1 ELSE 0 END) AS open,
            SUM(CASE WHEN LOWER(status) = 'removed' THEN 1 ELSE 0 END) AS removed,
            SUM(CASE WHEN LOWER(status) != 'removed' THEN 1 ELSE 0 END) AS visible
        FROM jobs
        """).fetchone()

    if row is None:
        return {"total": 0, "open": 0, "removed": 0, "visible": 0}

    return {
        "total": int(row["total"] or 0),
        "open": int(row["open"] or 0),
        "removed": int(row["removed"] or 0),
        "visible": int(row["visible"] or 0),
    }


def get_jobs_for_moderation(
    connection: sqlite3.Connection,
    *,
    status: str = "all",
    search: str = "",
    page: int = 1,
    per_page: int = JOBS_PER_PAGE,
) -> JobModerationPage:
    selected_status = status if status in JOB_STATUS_FILTERS else "all"
    cleaned_search = search.strip()
    requested_page = max(page, 1)
    safe_per_page = max(per_page, 1)
    conditions: list[str] = []
    parameters: list[object] = []

    if selected_status != "all":
        conditions.append("LOWER(jobs.status) = ?")
        parameters.append(selected_status)

    if cleaned_search:
        search_value = f"%{cleaned_search}%"
        conditions.append("""
            (
                jobs.title LIKE ? COLLATE NOCASE
                OR employers.company_name LIKE ? COLLATE NOCASE
                OR jobs.location LIKE ? COLLATE NOCASE
                OR COALESCE(jobs.category, '') LIKE ? COLLATE NOCASE
                OR jobs.description LIKE ? COLLATE NOCASE
            )
            """)
        parameters.extend([search_value] * 5)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    count_row = connection.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM jobs
        JOIN employers ON employers.employer_id = jobs.employer_id
        {where_clause}
        """,
        parameters,
    ).fetchone()
    total_jobs = int(count_row["total"]) if count_row is not None else 0
    total_pages = max(1, math.ceil(total_jobs / safe_per_page))
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * safe_per_page

    jobs = connection.execute(
        f"""
        SELECT
            jobs.job_id,
            jobs.title,
            jobs.description,
            jobs.location,
            jobs.employment_type,
            jobs.category,
            jobs.experience_level,
            jobs.work_mode,
            jobs.salary_min,
            jobs.salary_max,
            jobs.status,
            jobs.application_deadline,
            jobs.created_at,
            employers.company_name,
            employers.company_email,
            COUNT(applications.application_id) AS application_count
        FROM jobs
        JOIN employers ON employers.employer_id = jobs.employer_id
        LEFT JOIN applications ON applications.job_id = jobs.job_id
        {where_clause}
        GROUP BY jobs.job_id
        ORDER BY datetime(jobs.created_at) DESC, jobs.job_id DESC
        LIMIT ? OFFSET ?
        """,
        [*parameters, safe_per_page, offset],
    ).fetchall()

    return JobModerationPage(
        jobs=jobs,
        page=current_page,
        per_page=safe_per_page,
        total_jobs=total_jobs,
        total_pages=total_pages,
    )


def get_account_totals(connection: sqlite3.Connection) -> dict[str, int]:
    row = connection.execute("""
        SELECT
            (SELECT COUNT(*) FROM seekers) AS seekers,
            (SELECT COUNT(*) FROM employers) AS employers,
            (SELECT COUNT(*) FROM seekers WHERE is_active = 1)
                + (SELECT COUNT(*) FROM employers WHERE is_active = 1)
                AS active
        """).fetchone()

    if row is None:
        return {"all": 0, "seekers": 0, "employers": 0, "active": 0}

    seeker_total = int(row["seekers"])
    employer_total = int(row["employers"])
    return {
        "all": seeker_total + employer_total,
        "seekers": seeker_total,
        "employers": employer_total,
        "active": int(row["active"]),
    }


def get_registered_users(
    connection: sqlite3.Connection,
    *,
    account_type: str = "all",
    search: str = "",
    page: int = 1,
    per_page: int = USERS_PER_PAGE,
) -> UserListPage:
    selected_type = account_type if account_type in ACCOUNT_TYPES else "all"
    cleaned_search = search.strip()
    requested_page = max(page, 1)
    safe_per_page = max(per_page, 1)

    combined_query = """
        SELECT
            seeker_id AS account_id,
            full_name AS display_name,
            email,
            contact_number,
            'Job Seeker' AS account_type,
            'seeker' AS account_type_key,
            is_active,
            created_at
        FROM seekers

        UNION ALL

        SELECT
            employer_id AS account_id,
            company_name AS display_name,
            company_email AS email,
            contact_number,
            'Employer' AS account_type,
            'employer' AS account_type_key,
            is_active,
            created_at
        FROM employers
    """

    conditions: list[str] = []
    parameters: list[object] = []

    if selected_type != "all":
        conditions.append("account_type_key = ?")
        parameters.append(selected_type)

    if cleaned_search:
        search_value = f"%{cleaned_search}%"
        conditions.append("""
            (
                display_name LIKE ? COLLATE NOCASE
                OR email LIKE ? COLLATE NOCASE
                OR COALESCE(contact_number, '') LIKE ? COLLATE NOCASE
            )
            """)
        parameters.extend([search_value, search_value, search_value])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    count_row = connection.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM ({combined_query}) AS registered_users
        {where_clause}
        """,
        parameters,
    ).fetchone()
    total_users = int(count_row["total"]) if count_row is not None else 0
    total_pages = max(1, math.ceil(total_users / safe_per_page))
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * safe_per_page

    users = connection.execute(
        f"""
        SELECT *
        FROM ({combined_query}) AS registered_users
        {where_clause}
        ORDER BY datetime(created_at) DESC, account_type_key, account_id DESC
        LIMIT ? OFFSET ?
        """,
        [*parameters, safe_per_page, offset],
    ).fetchall()

    return UserListPage(
        users=users,
        page=current_page,
        per_page=safe_per_page,
        total_users=total_users,
        total_pages=total_pages,
    )


def set_user_account_active(
    connection: sqlite3.Connection,
    *,
    account_type: str,
    account_id: int,
    is_active: bool,
) -> str | None:
    """Update a seeker or employer account and return its display name."""

    account_configuration = {
        "seeker": ("seekers", "seeker_id", "full_name"),
        "employer": ("employers", "employer_id", "company_name"),
    }
    configuration = account_configuration.get(account_type)

    if configuration is None:
        return None

    table_name, id_column, name_column = configuration
    account = connection.execute(
        f"SELECT {name_column} AS display_name FROM {table_name} "
        f"WHERE {id_column} = ?",
        (account_id,),
    ).fetchone()

    if account is None:
        return None

    connection.execute(
        f"UPDATE {table_name} SET is_active = ? WHERE {id_column} = ?",
        (int(is_active), account_id),
    )
    connection.commit()
    return str(account["display_name"])


@admin_bp.route("/setup", methods=["GET", "POST"])
def setup() -> ResponseReturnValue:
    connection = get_db_connection()

    if count_admins(connection) > 0:
        connection.close()
        flash("Administrator setup has already been completed.", "info")
        return redirect(url_for("admin.login"))

    if request.method == "GET":
        connection.close()
        return render_template("admin_setup.html")

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    errors: list[str] = []

    if len(full_name) < 2:
        errors.append("Full name must contain at least 2 characters.")
    if not EMAIL_PATTERN.fullmatch(email):
        errors.append("Please enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must contain at least 8 characters.")
    if password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        connection.close()
        for error in errors:
            flash(error, "error")
        return render_template(
            "admin_setup.html",
            full_name=full_name,
            email=email,
        )

    try:
        cursor = connection.execute(
            """
            INSERT INTO admins (full_name, email, password_hash, role)
            VALUES (?, ?, ?, 'super_admin')
            """,
            (full_name, email, generate_password_hash(password)),
        )
        if cursor.lastrowid is None:
            raise sqlite3.IntegrityError("Admin ID was not generated.")
        admin_id = int(cursor.lastrowid)
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()
        flash("An administrator account already exists.", "error")
        return redirect(url_for("admin.login"))

    connection.close()
    session.clear()
    session["admin_id"] = admin_id
    session["admin_name"] = full_name
    session["admin_email"] = email
    session["admin_role"] = "super_admin"
    session["admin_authenticated"] = True
    flash("Administrator account created successfully.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    if session.get("admin_authenticated") is True:
        return redirect(url_for("admin.users"))

    connection = get_db_connection()
    if count_admins(connection) == 0:
        connection.close()
        return redirect(url_for("admin.setup"))

    if request.method == "GET":
        connection.close()
        return render_template("admin_login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    admin = connection.execute(
        """
        SELECT admin_id, full_name, email, password_hash, role, is_active
        FROM admins
        WHERE email = ?
        """,
        (email,),
    ).fetchone()
    connection.close()

    if admin is None or not check_password_hash(admin["password_hash"], password):
        flash("Incorrect email or password.", "error")
        return render_template("admin_login.html", email=email)

    if not bool(admin["is_active"]):
        flash("Your administrator account has been deactivated.", "error")
        return render_template("admin_login.html", email=email)

    session.clear()
    session["admin_id"] = int(admin["admin_id"])
    session["admin_name"] = admin["full_name"]
    session["admin_email"] = admin["email"]
    session["admin_role"] = admin["role"]
    session["admin_authenticated"] = True
    flash("Welcome back, administrator.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.post("/logout")
@admin_login_required
def logout() -> ResponseReturnValue:
    session.clear()
    flash("You have logged out successfully.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.get("/users")
@admin_login_required
def users() -> str:
    account_type = request.args.get("type", "all").strip().lower()
    if account_type not in ACCOUNT_TYPES:
        account_type = "all"

    search = request.args.get("search", "").strip()[:100]
    page = _positive_integer(request.args.get("page"), default=1)

    connection = get_db_connection()
    user_page = get_registered_users(
        connection,
        account_type=account_type,
        search=search,
        page=page,
    )
    totals = get_account_totals(connection)
    connection.close()

    return render_template(
        "admin_users.html",
        user_page=user_page,
        users=user_page.users,
        totals=totals,
        selected_type=account_type,
        search=search,
    )


@admin_bp.post("/users/<account_type>/<int:account_id>/status")
@admin_login_required
def update_user_status(account_type: str, account_id: int) -> ResponseReturnValue:
    if account_type not in {"seeker", "employer"}:
        abort(404)

    action = request.form.get("action", "").strip().lower()
    if action not in {"activate", "deactivate"}:
        flash("Select a valid account status action.", "error")
        return _user_list_redirect()

    connection = get_db_connection()
    display_name = set_user_account_active(
        connection,
        account_type=account_type,
        account_id=account_id,
        is_active=action == "activate",
    )
    connection.close()

    if display_name is None:
        abort(404)

    status_label = "reactivated" if action == "activate" else "deactivated"
    flash(f"{display_name}'s account has been {status_label}.", "success")
    return _user_list_redirect()


@admin_bp.get("/jobs")
@admin_login_required
def moderate_jobs() -> str:
    selected_status = request.args.get("status", "all").strip().lower()
    if selected_status not in JOB_STATUS_FILTERS:
        selected_status = "all"

    search = request.args.get("search", "").strip()[:100]
    page = _positive_integer(request.args.get("page"), default=1)
    connection = get_db_connection()
    job_page = get_jobs_for_moderation(
        connection,
        status=selected_status,
        search=search,
        page=page,
    )
    totals = get_job_moderation_totals(connection)
    connection.close()

    return render_template(
        "admin_jobs.html",
        job_page=job_page,
        jobs=job_page.jobs,
        totals=totals,
        selected_status=selected_status,
        search=search,
    )


@admin_bp.post("/jobs/<int:job_id>/moderation")
@admin_login_required
def update_job_moderation(job_id: int) -> ResponseReturnValue:
    action = request.form.get("action", "").strip().lower()
    if action not in {"remove", "restore"}:
        flash("Select a valid job moderation action.", "error")
        return _job_moderation_redirect()

    connection = get_db_connection()
    job = connection.execute(
        "SELECT title, status FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()

    if job is None:
        connection.close()
        abort(404)

    current_status = str(job["status"] or "")
    if action == "remove" and current_status == "Removed":
        connection.close()
        flash("This job posting has already been removed.", "info")
        return _job_moderation_redirect()

    if action == "restore" and current_status != "Removed":
        connection.close()
        flash("This job posting is already visible to its intended audience.", "info")
        return _job_moderation_redirect()

    target_status = "Removed" if action == "remove" else "Open"
    connection.execute(
        """
        UPDATE jobs
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE job_id = ?
        """,
        (target_status, job_id),
    )

    if action == "remove":
        connection.execute(
            "DELETE FROM job_notifications WHERE job_id = ?",
            (job_id,),
        )

    connection.commit()
    connection.close()

    action_label = "removed" if action == "remove" else "restored"
    flash(f"{job['title']} has been {action_label} successfully.", "success")
    return _job_moderation_redirect()


@admin_bp.get("/administrators")
@admin_login_required
@super_admin_required
def administrators() -> str:
    connection = get_db_connection()
    admin_accounts = get_administrators(connection)
    totals = get_admin_totals(connection)
    connection.close()
    return render_template(
        "admin_administrators.html",
        administrators=admin_accounts,
        totals=totals,
        allowed_roles=ADMIN_ROLES,
    )


@admin_bp.post("/administrators/add")
@admin_login_required
@super_admin_required
def add_administrator() -> ResponseReturnValue:
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    role = request.form.get("role", "admin").strip().lower()
    errors: list[str] = []

    if len(full_name) < 2:
        errors.append("Administrator name must contain at least 2 characters.")
    if not EMAIL_PATTERN.fullmatch(email):
        errors.append("Please enter a valid administrator email address.")
    if len(password) < 8:
        errors.append("Administrator password must contain at least 8 characters.")
    if password != confirm_password:
        errors.append("Administrator passwords do not match.")
    if role not in ADMIN_ROLES:
        errors.append("Select a valid administrator role.")

    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("admin.administrators"))

    connection = get_db_connection()
    try:
        connection.execute(
            """
            INSERT INTO admins (full_name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (full_name, email, generate_password_hash(password), role),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()
        flash("An administrator with this email already exists.", "error")
        return redirect(url_for("admin.administrators"))

    connection.close()
    flash(f"Administrator account for {full_name} was created.", "success")
    return redirect(url_for("admin.administrators"))


@admin_bp.post("/administrators/<int:admin_id>/status")
@admin_login_required
@super_admin_required
def update_administrator_status(admin_id: int) -> ResponseReturnValue:
    action = request.form.get("action", "").strip().lower()
    if action not in {"activate", "deactivate"}:
        flash("Select a valid administrator status action.", "error")
        return redirect(url_for("admin.administrators"))

    current_admin_id = int(session["admin_id"])
    if admin_id == current_admin_id and action == "deactivate":
        flash("You cannot deactivate your own administrator account.", "error")
        return redirect(url_for("admin.administrators"))

    connection = get_db_connection()
    target_admin = connection.execute(
        """
        SELECT admin_id, full_name, role, is_active
        FROM admins
        WHERE admin_id = ?
        """,
        (admin_id,),
    ).fetchone()

    if target_admin is None:
        connection.close()
        abort(404)

    if (
        action == "deactivate"
        and target_admin["role"] == "super_admin"
        and bool(target_admin["is_active"])
    ):
        active_super_admins = connection.execute("""
            SELECT COUNT(*) AS total
            FROM admins
            WHERE role = 'super_admin' AND is_active = 1
            """).fetchone()
        if active_super_admins is None or int(active_super_admins["total"]) <= 1:
            connection.close()
            flash("At least one active Super Admin is required.", "error")
            return redirect(url_for("admin.administrators"))

    connection.execute(
        "UPDATE admins SET is_active = ? WHERE admin_id = ?",
        (int(action == "activate"), admin_id),
    )
    connection.commit()
    connection.close()

    status_label = "reactivated" if action == "activate" else "deactivated"
    flash(
        f"{target_admin['full_name']}'s administrator account was {status_label}.",
        "success",
    )
    return redirect(url_for("admin.administrators"))


def _user_list_redirect() -> ResponseReturnValue:
    account_type = request.form.get("return_type", "all").strip().lower()
    if account_type not in ACCOUNT_TYPES:
        account_type = "all"

    search = request.form.get("return_search", "").strip()[:100]
    page = _positive_integer(request.form.get("return_page"), default=1)
    return redirect(
        url_for(
            "admin.users",
            type=account_type,
            search=search,
            page=page,
        )
    )


def _job_moderation_redirect() -> ResponseReturnValue:
    status = request.form.get("return_status", "all").strip().lower()
    if status not in JOB_STATUS_FILTERS:
        status = "all"

    search = request.form.get("return_search", "").strip()[:100]
    page = _positive_integer(request.form.get("return_page"), default=1)
    return redirect(
        url_for(
            "admin.moderate_jobs",
            status=status,
            search=search,
            page=page,
        )
    )


def _positive_integer(value: str | None, *, default: int) -> int:
    try:
        parsed_value = int(value) if value is not None else default
    except ValueError:
        return default
    return max(parsed_value, 1)
