import os
import sqlite3

from flask import current_app


def get_db_connection() -> sqlite3.Connection:
    path = current_app.config["DATABASE_PATH"]

    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    connection = sqlite3.connect(path)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    result = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return result is not None


def get_existing_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    if not table_exists(
        connection,
        table_name,
    ):
        return set()

    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()

    return {column["name"] for column in columns}


def add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
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


def init_database(app) -> None:
    with app.app_context():
        db = get_db_connection()

        db.executescript("""
            CREATE TABLE IF NOT EXISTS seekers (
                seeker_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                contact_number TEXT,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS employers (
                employer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                company_email TEXT NOT NULL UNIQUE,
                contact_number TEXT,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS seeker_profiles (
                profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL UNIQUE,
                job_title TEXT,
                location TEXT,
                about_me TEXT,
                job_categories TEXT,
                employment_type TEXT,
                preferred_location TEXT,
                expected_salary TEXT,
                profile_image TEXT,
                resume_filename TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS seeker_experiences (
                experience_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                position_title TEXT NOT NULL,
                company_name TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                description TEXT,

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS seeker_education (
                education_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                qualification TEXT NOT NULL,
                institution TEXT NOT NULL,
                start_year TEXT,
                end_year TEXT,
                status TEXT DEFAULT 'Completed',

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS seeker_skills (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,

                UNIQUE(seeker_id, skill_name),

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS seeker_certificates (
                certificate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                certificate_name TEXT NOT NULL,
                issuer TEXT,
                issue_date TEXT,
                certificate_filename TEXT,
                original_filename TEXT,

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS seeker_languages (
                language_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                language_name TEXT NOT NULL,
                proficiency TEXT NOT NULL,

                UNIQUE(seeker_id, language_name),

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE
            );

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
            );

            CREATE TABLE IF NOT EXISTS jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                employment_type TEXT NOT NULL,
                salary_min REAL,
                salary_max REAL,
                vacancies INTEGER NOT NULL DEFAULT 1,
                category TEXT,
                experience_level TEXT,
                work_mode TEXT,
                requirements TEXT,
                responsibilities TEXT,
                benefits TEXT,
                application_deadline TEXT,
                company_logo TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                is_featured INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,

                FOREIGN KEY (employer_id)
                    REFERENCES employers(employer_id)
                    ON DELETE CASCADE
            );

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
            );

            CREATE TABLE IF NOT EXISTS applications (
                application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                cover_letter TEXT,
                resume_filename TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(seeker_id, job_id),

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (job_id)
                    REFERENCES jobs(job_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_seekers_email
                ON seekers(email);

            CREATE INDEX IF NOT EXISTS idx_employers_email
                ON employers(company_email);

            CREATE INDEX IF NOT EXISTS idx_jobs_employer_id
                ON jobs(employer_id);

            CREATE INDEX IF NOT EXISTS idx_jobs_status
                ON jobs(status);

            CREATE INDEX IF NOT EXISTS idx_jobs_category
                ON jobs(category);

            CREATE INDEX IF NOT EXISTS idx_jobs_location
                ON jobs(location);

            CREATE INDEX IF NOT EXISTS idx_saved_jobs_seeker_id
                ON saved_jobs(seeker_id);

            CREATE INDEX IF NOT EXISTS idx_saved_jobs_job_id
                ON saved_jobs(job_id);

            CREATE INDEX IF NOT EXISTS idx_applications_seeker_id
                ON applications(seeker_id);

            CREATE INDEX IF NOT EXISTS idx_applications_job_id
                ON applications(job_id);

            CREATE INDEX IF NOT EXISTS idx_applications_status
                ON applications(status);
            """)

        seeker_profile_columns = {
            "job_title": "TEXT",
            "location": "TEXT",
            "about_me": "TEXT",
            "job_categories": "TEXT",
            "employment_type": "TEXT",
            "preferred_location": "TEXT",
            "expected_salary": "TEXT",
            "profile_image": "TEXT",
            "resume_filename": "TEXT",
            "updated_at": "TIMESTAMP",
        }

        for column_name, column_definition in seeker_profile_columns.items():
            add_column_if_missing(
                db,
                "seeker_profiles",
                column_name,
                column_definition,
            )

        certificate_columns = {
            "certificate_filename": "TEXT",
            "original_filename": "TEXT",
        }

        for column_name, column_definition in certificate_columns.items():
            add_column_if_missing(
                db,
                "seeker_certificates",
                column_name,
                column_definition,
            )

        employer_columns = {
            "company_name": "TEXT",
            "company_email": "TEXT",
            "contact_number": "TEXT",
            "password_hash": "TEXT",
            "created_at": "TIMESTAMP",
        }

        for column_name, column_definition in employer_columns.items():
            add_column_if_missing(
                db,
                "employers",
                column_name,
                column_definition,
            )

        company_profile_columns = {
            "company_name": "TEXT",
            "industry": "TEXT",
            "company_size": "TEXT",
            "address": "TEXT",
            "company_description": "TEXT",
            "contact_email": "TEXT",
            "contact_number": "TEXT",
            "website": "TEXT",
            "logo_url": "TEXT",
            "banner_url": "TEXT",
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        }

        for column_name, column_definition in company_profile_columns.items():
            add_column_if_missing(
                db,
                "company_profiles",
                column_name,
                column_definition,
            )

        job_columns = {
            "category": "TEXT",
            "experience_level": "TEXT",
            "work_mode": "TEXT",
            "requirements": "TEXT",
            "responsibilities": "TEXT",
            "benefits": "TEXT",
            "application_deadline": "TEXT",
            "company_logo": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'Open'",
            "is_featured": "INTEGER NOT NULL DEFAULT 0",
            "updated_at": "TIMESTAMP",
        }

        for column_name, column_definition in job_columns.items():
            add_column_if_missing(
                db,
                "jobs",
                column_name,
                column_definition,
            )

        application_columns = {
            "cover_letter": "TEXT",
            "resume_filename": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'Pending'",
            "applied_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        }

        for column_name, column_definition in application_columns.items():
            add_column_if_missing(
                db,
                "applications",
                column_name,
                column_definition,
            )

        db.commit()
        db.close()
