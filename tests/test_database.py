from src.database import get_db_connection


def test_database_contains_required_tables(app):
    with app.app_context():
        connection = get_db_connection()

        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """).fetchall()

        table_names = {table["name"] for table in tables}

        connection.close()

    required_tables = {
        "seekers",
        "employers",
        "company_profiles",
        "jobs",
        "saved_jobs",
        "applications",
    }

    assert required_tables.issubset(table_names)


def test_applications_table_columns(app):
    with app.app_context():
        connection = get_db_connection()

        columns = connection.execute("PRAGMA table_info(applications)").fetchall()

        column_names = {column["name"] for column in columns}

        connection.close()

    expected_columns = {
        "application_id",
        "seeker_id",
        "job_id",
        "cover_letter",
        "resume_filename",
        "status",
        "applied_at",
        "updated_at",
    }

    assert expected_columns.issubset(column_names)


def test_jobs_table_uses_title_column(app):
    with app.app_context():
        connection = get_db_connection()

        columns = connection.execute("PRAGMA table_info(jobs)").fetchall()

        column_names = {column["name"] for column in columns}

        connection.close()

    assert "title" in column_names
    assert "job_title" not in column_names
