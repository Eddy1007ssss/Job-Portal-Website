import pytest

from src.database import get_db_connection


def test_applications_table_exists(app):
    with app.app_context():
        connection = get_db_connection()

        table = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'applications'
            """).fetchone()

        connection.close()

    assert table is not None


def test_applications_table_has_required_columns(app):
    with app.app_context():
        connection = get_db_connection()

        columns = connection.execute("PRAGMA table_info(applications)").fetchall()

        connection.close()

    column_names = {column["name"] for column in columns}

    assert "application_id" in column_names
    assert "seeker_id" in column_names
    assert "job_id" in column_names
    assert "status" in column_names
    assert "applied_at" in column_names


@pytest.mark.skip(reason="The exact application submission route is not confirmed.")
def test_seeker_can_apply_for_job(client):
    pass


@pytest.mark.skip(reason="The exact My Applications route is not confirmed.")
def test_my_applications_page(client):
    pass


@pytest.mark.skip(reason="The application status update route is not implemented.")
def test_employer_updates_application_status(client):
    pass
