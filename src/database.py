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
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS employers (
                employer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                company_email TEXT NOT NULL UNIQUE,
                contact_number TEXT,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS admins (
                admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                is_active INTEGER NOT NULL DEFAULT 1,
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
                field_of_study TEXT,
                start_year TEXT,
                end_year TEXT,
                status TEXT DEFAULT 'Completed',
                certificate_filename TEXT,
                certificate_original_filename TEXT,

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

            CREATE TABLE IF NOT EXISTS job_notifications (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(seeker_id, job_id),

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (job_id)
                    REFERENCES jobs(job_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                reset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_type TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CHECK(account_type IN ('seeker', 'employer'))
            );

            CREATE TABLE IF NOT EXISTS interviews (
                interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL UNIQUE,
                employer_id INTEGER NOT NULL,
                scheduled_at TIMESTAMP NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                interview_mode TEXT NOT NULL,
                location_or_link TEXT NOT NULL,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                seeker_response_at TIMESTAMP,
                seeker_response_reason TEXT,
                cancellation_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CHECK(duration_minutes BETWEEN 15 AND 240),
                CHECK(interview_mode IN ('Online', 'In-person', 'Phone')),
                CHECK(status IN (
                    'Pending',
                    'Accepted',
                    'Declined',
                    'Cancelled',
                    'Completed'
                )),

                FOREIGN KEY (application_id)
                    REFERENCES applications(application_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (employer_id)
                    REFERENCES employers(employer_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS seeker_settings (
                settings_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL UNIQUE,
                email_notifications INTEGER NOT NULL DEFAULT 1,
                application_updates INTEGER NOT NULL DEFAULT 1,
                job_recommendations INTEGER NOT NULL DEFAULT 1,
                profile_visibility TEXT NOT NULL DEFAULT 'Employers',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (seeker_id)
                    REFERENCES seekers(seeker_id)
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

            CREATE TABLE IF NOT EXISTS employer_notifications (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employer_id INTEGER NOT NULL,
                event_key TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                application_id INTEGER,
                interview_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(employer_id, event_key),

                CHECK(notification_type IN (
                    'new_application',
                    'application_withdrawn',
                    'interview_accepted',
                    'interview_declined'
                )),

                FOREIGN KEY (employer_id)
                    REFERENCES employers(employer_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (application_id)
                    REFERENCES applications(application_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (interview_id)
                    REFERENCES interviews(interview_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_seekers_email
                ON seekers(email);

            CREATE INDEX IF NOT EXISTS idx_employers_email
                ON employers(company_email);

            CREATE INDEX IF NOT EXISTS idx_admins_email
                ON admins(email);

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

            CREATE INDEX IF NOT EXISTS idx_job_notifications_seeker_id
                ON job_notifications(seeker_id);

            CREATE INDEX IF NOT EXISTS idx_job_notifications_unread
                ON job_notifications(seeker_id, is_read);

            CREATE INDEX IF NOT EXISTS idx_password_reset_token_hash
                ON password_reset_tokens(token_hash);

            CREATE INDEX IF NOT EXISTS idx_password_reset_account
                ON password_reset_tokens(account_type, account_id);

            CREATE INDEX IF NOT EXISTS idx_interviews_employer_id
                ON interviews(employer_id);

            CREATE INDEX IF NOT EXISTS idx_interviews_status
                ON interviews(status);

            CREATE INDEX IF NOT EXISTS idx_interviews_scheduled_at
                ON interviews(scheduled_at);

            CREATE INDEX IF NOT EXISTS idx_applications_seeker_id
                ON applications(seeker_id);

            CREATE INDEX IF NOT EXISTS idx_applications_job_id
                ON applications(job_id);

            CREATE INDEX IF NOT EXISTS idx_applications_status
                ON applications(status);

            CREATE INDEX IF NOT EXISTS idx_employer_notifications_employer
                ON employer_notifications(employer_id);

            CREATE INDEX IF NOT EXISTS idx_employer_notifications_unread
                ON employer_notifications(employer_id, is_read);
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

        education_columns = {
            "field_of_study": "TEXT",
            "certificate_filename": "TEXT",
            "certificate_original_filename": "TEXT",
        }

        for column_name, column_definition in education_columns.items():
            add_column_if_missing(
                db,
                "seeker_education",
                column_name,
                column_definition,
            )

        employer_columns = {
            "company_name": "TEXT",
            "company_email": "TEXT",
            "contact_number": "TEXT",
            "password_hash": "TEXT",
            "is_active": "INTEGER NOT NULL DEFAULT 1",
            "created_at": "TIMESTAMP",
        }

        for column_name, column_definition in employer_columns.items():
            add_column_if_missing(
                db,
                "employers",
                column_name,
                column_definition,
            )

        seeker_columns = {
            "is_active": "INTEGER NOT NULL DEFAULT 1",
        }

        for column_name, column_definition in seeker_columns.items():
            add_column_if_missing(
                db,
                "seekers",
                column_name,
                column_definition,
            )

        admin_columns = {
            "role": "TEXT NOT NULL DEFAULT 'admin'",
            "is_active": "INTEGER NOT NULL DEFAULT 1",
        }

        for column_name, column_definition in admin_columns.items():
            add_column_if_missing(
                db,
                "admins",
                column_name,
                column_definition,
            )

        db.execute("""
            UPDATE admins
            SET role = 'super_admin'
            WHERE admin_id = (SELECT MIN(admin_id) FROM admins)
              AND NOT EXISTS (
                  SELECT 1
                  FROM admins
                  WHERE role = 'super_admin'
              )
            """)

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

        interview_columns = {
            "seeker_response_reason": "TEXT",
            "cancellation_reason": "TEXT",
        }

        for column_name, column_definition in interview_columns.items():
            add_column_if_missing(
                db,
                "interviews",
                column_name,
                column_definition,
            )

        db.commit()
        db.close()
