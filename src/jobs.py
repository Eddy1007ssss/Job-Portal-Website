from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from typing import Any

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

jobs_bp = Blueprint(
    "jobs",
    __name__,
)


JOBS_PER_PAGE = 6


SORT_OPTIONS = {
    "newest": "jobs.created_at DESC",
    "oldest": "jobs.created_at ASC",
    "salary_high": """
        COALESCE(jobs.salary_max, jobs.salary_min, 0) DESC
    """,
    "salary_low": """
        COALESCE(jobs.salary_min, jobs.salary_max, 0) ASC
    """,
    "title_az": "jobs.title COLLATE NOCASE ASC",
}


@dataclass
class JobFilters:
    keyword: str
    location: str
    category: str
    employment_type: str
    experience_level: str
    work_mode: str
    minimum_salary: int | None
    maximum_salary: int | None
    sort: str
    page: int


def get_existing_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    """
    Return all column names for a SQLite table.
    """

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()

    return {row["name"] for row in rows}


def add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    """
    Add a new SQLite column only when it does not exist.
    """

    existing_columns = get_existing_columns(
        connection,
        table_name,
    )

    if column_name in existing_columns:
        return

    connection.execute(f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name} {column_definition}
        """)


def initialise_job_tables() -> None:
    """
    Create the job listing and saved job tables.

    This function also adds missing columns to an older jobs table.
    """

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,

            employer_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            location TEXT NOT NULL,

            employment_type TEXT NOT NULL,

            salary_min REAL,

            salary_max REAL,

            status TEXT NOT NULL DEFAULT 'Open',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (employer_id)
                REFERENCES employers(employer_id)
                ON DELETE CASCADE
        )
        """)

    additional_columns = {
        "category": "TEXT",
        "experience_level": "TEXT",
        "work_mode": "TEXT",
        "requirements": "TEXT",
        "responsibilities": "TEXT",
        "benefits": "TEXT",
        "application_deadline": "TEXT",
        "company_logo": "TEXT",
        "is_featured": "INTEGER NOT NULL DEFAULT 0",
        "updated_at": "TIMESTAMP",
    }

    for column_name, column_definition in additional_columns.items():
        add_column_if_missing(
            connection,
            "jobs",
            column_name,
            column_definition,
        )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS saved_jobs (
            saved_job_id INTEGER PRIMARY KEY AUTOINCREMENT,

            seeker_id INTEGER NOT NULL,

            job_id INTEGER NOT NULL,

            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(seeker_id, job_id),

            FOREIGN KEY (seeker_id)
                REFERENCES seekers(seeker_id)
                ON DELETE CASCADE,

            FOREIGN KEY (job_id)
                REFERENCES jobs(job_id)
                ON DELETE CASCADE
        )
        """)

    connection.commit()
    connection.close()


def get_or_create_demo_employer(
    connection: sqlite3.Connection,
    company_name: str,
    company_email: str,
    contact_number: str,
) -> int:
    """
    Find an employer by email or create a demonstration employer.
    """

    employer = connection.execute(
        """
        SELECT employer_id
        FROM employers
        WHERE company_email = ?
        """,
        (company_email,),
    ).fetchone()

    if employer:
        return int(employer["employer_id"])

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
            "demo-account-not-for-login",
        ),
    )

    return int(cursor.lastrowid)


def seed_demo_jobs() -> None:
    """
    Add sample jobs only when the jobs table is empty.
    """

    connection = get_db_connection()

    total_jobs = connection.execute("""
        SELECT COUNT(*) AS total
        FROM jobs
        """).fetchone()["total"]

    if total_jobs > 0:
        connection.close()
        return

    employers = {
        "Spotify": get_or_create_demo_employer(
            connection,
            "Spotify",
            "careers@spotify-demo.com",
            "+1 212 555 0101",
        ),
        "Google": get_or_create_demo_employer(
            connection,
            "Google",
            "careers@google-demo.com",
            "+1 650 555 0102",
        ),
        "HubSpot": get_or_create_demo_employer(
            connection,
            "HubSpot",
            "careers@hubspot-demo.com",
            "+1 617 555 0103",
        ),
        "Microsoft": get_or_create_demo_employer(
            connection,
            "Microsoft",
            "careers@microsoft-demo.com",
            "+1 425 555 0104",
        ),
        "Zendesk": get_or_create_demo_employer(
            connection,
            "Zendesk",
            "careers@zendesk-demo.com",
            "+1 415 555 0105",
        ),
        "Airbnb": get_or_create_demo_employer(
            connection,
            "Airbnb",
            "careers@airbnb-demo.com",
            "+1 415 555 0106",
        ),
        "Amazon": get_or_create_demo_employer(
            connection,
            "Amazon",
            "careers@amazon-demo.com",
            "+1 206 555 0107",
        ),
        "Adobe": get_or_create_demo_employer(
            connection,
            "Adobe",
            "careers@adobe-demo.com",
            "+1 408 555 0108",
        ),
    }

    demo_jobs = [
        {
            "employer_id": employers["Spotify"],
            "title": "Senior UI/UX Designer",
            "description": (
                "Design user-centred digital experiences for music "
                "products used by millions of users worldwide."
            ),
            "location": "New York, USA",
            "employment_type": "Full-time",
            "salary_min": 90000,
            "salary_max": 120000,
            "category": "Design",
            "experience_level": "Senior Level",
            "work_mode": "On-site",
            "requirements": (
                "At least five years of UI/UX design experience. "
                "Strong knowledge of Figma and design systems."
            ),
            "responsibilities": (
                "Create wireframes, prototypes and production-ready "
                "interfaces. Work closely with product teams."
            ),
            "benefits": (
                "Health insurance, annual bonus, paid leave and "
                "professional development support."
            ),
            "application_deadline": "2026-09-30",
            "is_featured": 1,
        },
        {
            "employer_id": employers["Google"],
            "title": "Frontend Developer",
            "description": (
                "Build responsive, accessible and scalable interfaces "
                "for modern web applications."
            ),
            "location": "Remote",
            "employment_type": "Full-time",
            "salary_min": 100000,
            "salary_max": 135000,
            "category": "Development",
            "experience_level": "Mid Level",
            "work_mode": "Remote",
            "requirements": (
                "Strong JavaScript, HTML and CSS knowledge. "
                "Experience with React or Angular."
            ),
            "responsibilities": (
                "Develop frontend components, write automated tests "
                "and participate in code reviews."
            ),
            "benefits": (
                "Remote working allowance, medical coverage and "
                "annual learning budget."
            ),
            "application_deadline": "2026-10-15",
            "is_featured": 1,
        },
        {
            "employer_id": employers["HubSpot"],
            "title": "Digital Marketing Manager",
            "description": (
                "Plan and manage digital campaigns that improve "
                "customer acquisition and brand awareness."
            ),
            "location": "Boston, USA",
            "employment_type": "Full-time",
            "salary_min": 80000,
            "salary_max": 110000,
            "category": "Marketing",
            "experience_level": "Mid Level",
            "work_mode": "Hybrid",
            "requirements": (
                "Experience with content marketing, SEO and campaign " "analytics."
            ),
            "responsibilities": (
                "Manage marketing campaigns, monitor performance and "
                "prepare monthly reports."
            ),
            "benefits": (
                "Flexible working hours, health insurance and " "performance bonus."
            ),
            "application_deadline": "2026-09-25",
            "is_featured": 0,
        },
        {
            "employer_id": employers["Microsoft"],
            "title": "Product Manager",
            "description": (
                "Define product strategy and coordinate delivery "
                "across design, engineering and business teams."
            ),
            "location": "Redmond, USA",
            "employment_type": "Full-time",
            "salary_min": 95000,
            "salary_max": 125000,
            "category": "Product",
            "experience_level": "Senior Level",
            "work_mode": "Hybrid",
            "requirements": (
                "Strong product management and communication skills. "
                "Experience working with Agile teams."
            ),
            "responsibilities": (
                "Maintain the product roadmap, gather requirements "
                "and monitor product performance."
            ),
            "benefits": (
                "Medical benefits, stock options and flexible work " "arrangements."
            ),
            "application_deadline": "2026-10-10",
            "is_featured": 1,
        },
        {
            "employer_id": employers["Zendesk"],
            "title": "Customer Support Specialist",
            "description": (
                "Help customers resolve technical questions and "
                "provide a professional support experience."
            ),
            "location": "Remote",
            "employment_type": "Full-time",
            "salary_min": 45000,
            "salary_max": 60000,
            "category": "Customer Support",
            "experience_level": "Entry Level",
            "work_mode": "Remote",
            "requirements": (
                "Excellent communication skills and basic technical "
                "troubleshooting knowledge."
            ),
            "responsibilities": (
                "Respond to customer enquiries, document solutions "
                "and escalate complex issues."
            ),
            "benefits": (
                "Remote work allowance, paid training and medical " "insurance."
            ),
            "application_deadline": "2026-09-20",
            "is_featured": 0,
        },
        {
            "employer_id": employers["Airbnb"],
            "title": "Data Analyst",
            "description": (
                "Analyse product and customer data to identify trends "
                "and support business decisions."
            ),
            "location": "San Francisco, USA",
            "employment_type": "Contract",
            "salary_min": 70000,
            "salary_max": 90000,
            "category": "Data",
            "experience_level": "Mid Level",
            "work_mode": "Hybrid",
            "requirements": (
                "Experience with SQL, Excel and data visualisation " "tools."
            ),
            "responsibilities": (
                "Prepare dashboards, analyse performance indicators "
                "and present findings."
            ),
            "benefits": (
                "Flexible schedule, project completion bonus and " "travel allowance."
            ),
            "application_deadline": "2026-09-28",
            "is_featured": 0,
        },
        {
            "employer_id": employers["Amazon"],
            "title": "Backend Developer",
            "description": (
                "Develop reliable APIs and cloud services for "
                "high-volume applications."
            ),
            "location": "Seattle, USA",
            "employment_type": "Full-time",
            "salary_min": 105000,
            "salary_max": 145000,
            "category": "Development",
            "experience_level": "Senior Level",
            "work_mode": "On-site",
            "requirements": (
                "Strong Python, Java or Node.js experience. "
                "Knowledge of databases and cloud services."
            ),
            "responsibilities": (
                "Design APIs, optimise database queries and maintain "
                "backend services."
            ),
            "benefits": ("Stock options, health insurance and employee " "discounts."),
            "application_deadline": "2026-10-20",
            "is_featured": 1,
        },
        {
            "employer_id": employers["Adobe"],
            "title": "Graphic Designer",
            "description": (
                "Create visual assets for brand, social media and "
                "product marketing campaigns."
            ),
            "location": "San Jose, USA",
            "employment_type": "Part-time",
            "salary_min": 50000,
            "salary_max": 70000,
            "category": "Design",
            "experience_level": "Entry Level",
            "work_mode": "Hybrid",
            "requirements": (
                "Portfolio demonstrating graphic design skills. "
                "Knowledge of Adobe Creative Cloud."
            ),
            "responsibilities": (
                "Create marketing graphics, maintain brand consistency "
                "and collaborate with the marketing team."
            ),
            "benefits": (
                "Flexible working hours, software allowance and paid " "training."
            ),
            "application_deadline": "2026-09-22",
            "is_featured": 0,
        },
    ]

    for job in demo_jobs:
        connection.execute(
            """
            INSERT INTO jobs (
                employer_id,
                title,
                description,
                location,
                employment_type,
                salary_min,
                salary_max,
                status,
                category,
                experience_level,
                work_mode,
                requirements,
                responsibilities,
                benefits,
                application_deadline,
                company_logo,
                is_featured
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, 'Open',
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                job["employer_id"],
                job["title"],
                job["description"],
                job["location"],
                job["employment_type"],
                job["salary_min"],
                job["salary_max"],
                job["category"],
                job["experience_level"],
                job["work_mode"],
                job["requirements"],
                job["responsibilities"],
                job["benefits"],
                job["application_deadline"],
                "images/company-placeholder.png",
                job["is_featured"],
            ),
        )

    connection.commit()
    connection.close()


def parse_optional_integer(
    value: str | None,
) -> int | None:
    """
    Convert an optional query parameter to an integer.
    """

    if value is None:
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    try:
        return int(cleaned_value)
    except ValueError:
        return None


def read_job_filters() -> JobFilters:
    """
    Read and validate all job-listing query parameters.
    """

    requested_page = parse_optional_integer(request.args.get("page"))

    page = requested_page or 1

    sort = request.args.get(
        "sort",
        "newest",
    ).strip()

    if sort not in SORT_OPTIONS:
        sort = "newest"

    return JobFilters(
        keyword=request.args.get(
            "keyword",
            "",
        ).strip(),
        location=request.args.get(
            "location",
            "",
        ).strip(),
        category=request.args.get(
            "category",
            "",
        ).strip(),
        employment_type=request.args.get(
            "employment_type",
            "",
        ).strip(),
        experience_level=request.args.get(
            "experience_level",
            "",
        ).strip(),
        work_mode=request.args.get(
            "work_mode",
            "",
        ).strip(),
        minimum_salary=parse_optional_integer(request.args.get("minimum_salary")),
        maximum_salary=parse_optional_integer(request.args.get("maximum_salary")),
        sort=sort,
        page=max(page, 1),
    )


def build_job_filter_query(
    filters: JobFilters,
) -> tuple[str, list[Any]]:
    """
    Build a safe SQL WHERE condition and its parameters.
    """

    conditions = [
        "jobs.status = 'Open'",
    ]

    parameters: list[Any] = []

    if filters.keyword:
        keyword = f"%{filters.keyword}%"

        conditions.append("""
            (
                jobs.title LIKE ?
                OR employers.company_name LIKE ?
                OR jobs.description LIKE ?
                OR jobs.category LIKE ?
            )
            """)

        parameters.extend(
            [
                keyword,
                keyword,
                keyword,
                keyword,
            ]
        )

    if filters.location:
        conditions.append("jobs.location LIKE ?")

        parameters.append(f"%{filters.location}%")

    if filters.category:
        conditions.append("jobs.category = ?")

        parameters.append(filters.category)

    if filters.employment_type:
        conditions.append("jobs.employment_type = ?")

        parameters.append(filters.employment_type)

    if filters.experience_level:
        conditions.append("jobs.experience_level = ?")

        parameters.append(filters.experience_level)

    if filters.work_mode:
        conditions.append("jobs.work_mode = ?")

        parameters.append(filters.work_mode)

    if filters.minimum_salary is not None:
        conditions.append("""
            COALESCE(
                jobs.salary_max,
                jobs.salary_min,
                0
            ) >= ?
            """)

        parameters.append(filters.minimum_salary)

    if filters.maximum_salary is not None:
        conditions.append("""
            COALESCE(
                jobs.salary_min,
                jobs.salary_max,
                0
            ) <= ?
            """)

        parameters.append(filters.maximum_salary)

    where_clause = " AND ".join(conditions)

    return where_clause, parameters


def get_current_seeker_id() -> int | None:
    """
    Return the logged-in seeker ID from the session.
    """

    seeker_id = session.get("seeker_id")

    if seeker_id is None:
        return None

    try:
        return int(seeker_id)
    except (TypeError, ValueError):
        return None


@jobs_bp.route("/jobs")
def list_jobs():
    """
    Display searchable and filterable job listings.
    """

    initialise_job_tables()
    seed_demo_jobs()

    filters = read_job_filters()

    where_clause, query_parameters = build_job_filter_query(filters)

    order_by = SORT_OPTIONS[filters.sort]

    connection = get_db_connection()

    total_jobs = connection.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM jobs

        JOIN employers
            ON employers.employer_id =
               jobs.employer_id

        WHERE {where_clause}
        """,
        query_parameters,
    ).fetchone()["total"]

    total_pages = max(
        math.ceil(total_jobs / JOBS_PER_PAGE),
        1,
    )

    current_page = min(
        filters.page,
        total_pages,
    )

    offset = (current_page - 1) * JOBS_PER_PAGE

    seeker_id = get_current_seeker_id()

    jobs = connection.execute(
        f"""
        SELECT
            jobs.job_id,
            jobs.employer_id,
            jobs.title,
            jobs.description,
            jobs.location,
            jobs.employment_type,
            jobs.salary_min,
            jobs.salary_max,
            jobs.status,
            jobs.created_at,
            jobs.category,
            jobs.experience_level,
            jobs.work_mode,
            jobs.application_deadline,
            jobs.company_logo,
            jobs.is_featured,

            employers.company_name,

            CASE
                WHEN saved_jobs.saved_job_id
                    IS NULL
                THEN 0
                ELSE 1
            END AS is_saved

        FROM jobs

        JOIN employers
            ON employers.employer_id =
               jobs.employer_id

        LEFT JOIN saved_jobs
            ON saved_jobs.job_id =
               jobs.job_id
            AND saved_jobs.seeker_id = ?

        WHERE {where_clause}

        ORDER BY {order_by}

        LIMIT ?
        OFFSET ?
        """,
        [
            seeker_id,
            *query_parameters,
            JOBS_PER_PAGE,
            offset,
        ],
    ).fetchall()

    categories = connection.execute("""
        SELECT DISTINCT category
        FROM jobs
        WHERE category IS NOT NULL
          AND TRIM(category) != ''
        ORDER BY category
        """).fetchall()

    locations = connection.execute("""
        SELECT DISTINCT location
        FROM jobs
        WHERE location IS NOT NULL
          AND TRIM(location) != ''
        ORDER BY location
        """).fetchall()

    connection.close()

    return render_template(
        "job_listings.html",
        jobs=jobs,
        filters=filters,
        categories=categories,
        locations=locations,
        total_jobs=total_jobs,
        current_page=current_page,
        total_pages=total_pages,
    )


@jobs_bp.route("/jobs/<int:job_id>")
def job_details(job_id: int):
    connection = get_db_connection()
    seeker_id = session.get("seeker_id")

    job = connection.execute(
        """
        SELECT
            jobs.*,
            employers.company_name,
            employers.company_email
        FROM jobs
        JOIN employers
            ON employers.employer_id = jobs.employer_id
        WHERE jobs.job_id = ?
        """,
        (job_id,),
    ).fetchone()

    if job is None:
        connection.close()

        flash(
            "The requested job was not found.",
            "error",
        )

        return redirect(url_for("jobs.list_jobs"))

    has_applied = False
    is_saved = False

    if seeker_id:
        existing_application = connection.execute(
            """
            SELECT application_id
            FROM applications
            WHERE seeker_id = ?
              AND job_id = ?
            """,
            (
                seeker_id,
                job_id,
            ),
        ).fetchone()

        has_applied = existing_application is not None

        saved_job = connection.execute(
            """
            SELECT saved_job_id
            FROM saved_jobs
            WHERE seeker_id = ?
              AND job_id = ?
            """,
            (
                seeker_id,
                job_id,
            ),
        ).fetchone()

        is_saved = saved_job is not None

    job_data = dict(job)
    job_data["is_saved"] = is_saved

    connection.close()

    return render_template(
        "job_details.html",
        job=job_data,
        has_applied=has_applied,
    )


@jobs_bp.post("/jobs/<int:job_id>/save")
def toggle_save_job(
    job_id: int,
):
    """
    Save or unsave a job for the logged-in seeker.
    """

    seeker_id = get_current_seeker_id()

    if seeker_id is None:
        flash(
            "Please log in as a job seeker to save jobs.",
            "error",
        )

        return redirect(url_for("seeker.login"))

    initialise_job_tables()

    connection = get_db_connection()

    job = connection.execute(
        """
        SELECT job_id
        FROM jobs
        WHERE job_id = ?
          AND status = 'Open'
        """,
        (job_id,),
    ).fetchone()

    if job is None:
        connection.close()

        flash(
            "The selected job is no longer available.",
            "error",
        )

        return redirect(url_for("jobs.list_jobs"))

    saved_job = connection.execute(
        """
        SELECT saved_job_id
        FROM saved_jobs
        WHERE seeker_id = ?
          AND job_id = ?
        """,
        (
            seeker_id,
            job_id,
        ),
    ).fetchone()

    if saved_job:
        connection.execute(
            """
            DELETE FROM saved_jobs
            WHERE seeker_id = ?
              AND job_id = ?
            """,
            (
                seeker_id,
                job_id,
            ),
        )

        message = "Job removed from your saved jobs."
    else:
        connection.execute(
            """
            INSERT INTO saved_jobs (
                seeker_id,
                job_id
            )
            VALUES (?, ?)
            """,
            (
                seeker_id,
                job_id,
            ),
        )

        message = "Job saved successfully."

    connection.commit()
    connection.close()

    flash(
        message,
        "success",
    )

    return_url = request.form.get(
        "next",
        "",
    )

    if return_url and return_url.startswith("/") and not return_url.startswith("//"):
        return redirect(return_url)

    return redirect(
        url_for(
            "jobs.job_details",
            job_id=job_id,
        )
    )
