import re

from src.database import get_db_connection


def create_employer(
    app,
    company_name: str,
    company_email: str,
) -> int:
    with app.app_context():
        connection = get_db_connection()
        cursor = connection.execute(
            """
            INSERT INTO employers (
                company_name,
                company_email,
                password_hash
            )
            VALUES (?, ?, ?)
            """,
            (
                company_name,
                company_email,
                "test-password-hash",
            ),
        )
        assert cursor.lastrowid is not None
        employer_id = int(cursor.lastrowid)
        connection.commit()
        connection.close()

    return employer_id


def create_job(
    app,
    employer_id: int,
    title: str,
    status: str = "Open",
) -> int:
    with app.app_context():
        connection = get_db_connection()
        cursor = connection.execute(
            """
            INSERT INTO jobs (
                employer_id,
                title,
                description,
                location,
                employment_type,
                status,
                application_deadline
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employer_id,
                title,
                "Test job description",
                "Kuala Lumpur",
                "Full-time",
                status,
                "2026-09-30",
            ),
        )
        assert cursor.lastrowid is not None
        job_id = int(cursor.lastrowid)
        connection.commit()
        connection.close()

    return job_id


def create_application(app, job_id: int, number: int) -> None:
    with app.app_context():
        connection = get_db_connection()

        for index in range(number):
            cursor = connection.execute(
                """
                INSERT INTO seekers (
                    full_name,
                    email,
                    password_hash
                )
                VALUES (?, ?, ?)
                """,
                (
                    f"Test Seeker {job_id}-{index}",
                    f"seeker-{job_id}-{index}@example.com",
                    "test-password-hash",
                ),
            )
            assert cursor.lastrowid is not None
            seeker_id = int(cursor.lastrowid)

            connection.execute(
                """
                INSERT INTO applications (
                    seeker_id,
                    job_id,
                    status
                )
                VALUES (?, ?, ?)
                """,
                (
                    seeker_id,
                    job_id,
                    "Pending",
                ),
            )

        connection.commit()
        connection.close()


def log_in_employer(
    client,
    employer_id: int,
    company_name: str,
    company_email: str,
) -> None:
    with client.session_transaction() as session:
        session["employer_id"] = employer_id
        session["employer_company_name"] = company_name
        session["employer_email"] = company_email


def get_job(app, job_id: int):
    with app.app_context():
        connection = get_db_connection()
        job = connection.execute(
            """
            SELECT job_id, employer_id, title, status
            FROM jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()
        connection.close()

    return job


def test_employer_jobs_requires_employer_login(client):
    response = client.get("/employer/jobs")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/employer/login")


def test_employer_sees_only_company_jobs_and_application_counts(app, client):
    employer_id = create_employer(
        app,
        "Logged Company",
        "logged@example.com",
    )
    other_employer_id = create_employer(
        app,
        "Other Company",
        "other@example.com",
    )

    active_job_id = create_job(
        app,
        employer_id,
        "Backend Developer",
    )
    create_job(
        app,
        employer_id,
        "Closed Designer Role",
        status="Closed",
    )
    create_job(
        app,
        other_employer_id,
        "Other Company Job",
    )
    create_application(app, active_job_id, 2)

    log_in_employer(
        client,
        employer_id,
        "Logged Company",
        "logged@example.com",
    )

    response = client.get("/employer/jobs")

    assert response.status_code == 200
    assert b"Backend Developer" in response.data
    assert b"Closed Designer Role" in response.data
    assert b"Other Company Job" not in response.data
    assert b"employer_jobs.css" in response.data
    assert f"/employer/jobs/{active_job_id}/status".encode() in response.data
    assert f"/employer/jobs/{active_job_id}/delete".encode() in response.data
    assert re.search(
        r">\s*2\s*</strong>\s*<span>\s*applications",
        response.get_data(as_text=True),
    )
    assert b"Active" in response.data
    assert b"Closed" in response.data
    assert client.get("/static/css/employer_jobs.css").status_code == 200


def test_employer_can_close_and_reopen_own_job(app, client):
    employer_id = create_employer(
        app,
        "Logged Company",
        "logged@example.com",
    )
    job_id = create_job(
        app,
        employer_id,
        "Backend Developer",
    )

    log_in_employer(
        client,
        employer_id,
        "Logged Company",
        "logged@example.com",
    )

    close_response = client.post(
        f"/employer/jobs/{job_id}/status",
        data={"status": "Closed"},
    )

    assert close_response.status_code == 302
    assert close_response.headers["Location"].endswith("/employer/jobs")
    assert get_job(app, job_id)["status"] == "Closed"

    reopen_response = client.post(
        f"/employer/jobs/{job_id}/status",
        data={"status": "Open"},
    )

    assert reopen_response.status_code == 302
    assert get_job(app, job_id)["status"] == "Open"


def test_employer_cannot_manage_another_company_job(app, client):
    employer_id = create_employer(
        app,
        "Logged Company",
        "logged@example.com",
    )
    other_employer_id = create_employer(
        app,
        "Other Company",
        "other@example.com",
    )
    other_job_id = create_job(
        app,
        other_employer_id,
        "Other Company Job",
    )

    log_in_employer(
        client,
        employer_id,
        "Logged Company",
        "logged@example.com",
    )

    status_response = client.post(
        f"/employer/jobs/{other_job_id}/status",
        data={"status": "Closed"},
    )
    delete_response = client.post(
        f"/employer/jobs/{other_job_id}/delete",
    )

    assert status_response.status_code == 302
    assert delete_response.status_code == 302
    assert get_job(app, other_job_id)["status"] == "Open"


def test_employer_can_delete_own_job_and_its_applications(app, client):
    employer_id = create_employer(
        app,
        "Logged Company",
        "logged@example.com",
    )
    job_id = create_job(
        app,
        employer_id,
        "Temporary Job",
    )
    create_application(app, job_id, 1)

    log_in_employer(
        client,
        employer_id,
        "Logged Company",
        "logged@example.com",
    )

    response = client.post(f"/employer/jobs/{job_id}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/employer/jobs")
    assert get_job(app, job_id) is None

    with app.app_context():
        connection = get_db_connection()
        application_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM applications
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()[0]
        connection.close()

    assert application_count == 0
