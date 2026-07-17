from werkzeug.security import generate_password_hash

from src.database import get_db_connection


def create_employer(app):
    with app.app_context():
        connection = get_db_connection()

        existing_employer = connection.execute(
            """
            SELECT employer_id
            FROM employers
            WHERE company_email = ?
            """,
            ("jobs-test-employer@example.com",),
        ).fetchone()

        if existing_employer:
            employer_id = existing_employer["employer_id"]

            connection.close()

            return employer_id

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
                "Jobs Test Company",
                "jobs-test-employer@example.com",
                "0123456789",
                generate_password_hash("Password123"),
            ),
        )

        employer_id = cursor.lastrowid

        connection.commit()
        connection.close()

    return employer_id


def create_job(app, employer_id):
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
                salary_min,
                salary_max,
                status,
                category,
                experience_level,
                work_mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employer_id,
                "Junior Software Engineer",
                "Develop and test web applications.",
                "Kuala Lumpur",
                "Full-time",
                3000,
                4500,
                "Open",
                "Development",
                "Entry Level",
                "Hybrid",
            ),
        )

        job_id = cursor.lastrowid

        connection.commit()
        connection.close()

    return job_id


def create_seeker(app):
    with app.app_context():
        connection = get_db_connection()

        existing_seeker = connection.execute(
            """
            SELECT seeker_id
            FROM seekers
            WHERE email = ?
            """,
            ("job-test-seeker@example.com",),
        ).fetchone()

        if existing_seeker:
            seeker_id = existing_seeker["seeker_id"]

            connection.close()

            return seeker_id

        cursor = connection.execute(
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
                "Test Job Seeker",
                "job-test-seeker@example.com",
                "0198765432",
                generate_password_hash("Password123"),
            ),
        )

        seeker_id = cursor.lastrowid

        connection.commit()
        connection.close()

    return seeker_id


def login_seeker(client, seeker_id):
    with client.session_transaction() as session:
        session["seeker_id"] = seeker_id


def test_job_list_page_loads(client):
    response = client.get("/jobs")

    assert response.status_code == 200


def test_created_job_appears_in_job_list(
    client,
    app,
):
    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
    )

    response = client.get("/jobs")

    assert response.status_code == 200
    assert b"Junior Software Engineer" in response.data


def test_job_details_page(
    client,
    app,
):
    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
    )

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    assert b"Junior Software Engineer" in response.data
    assert b"Kuala Lumpur" in response.data


def test_nonexistent_job_redirects_to_job_list(
    client,
):
    response = client.get(
        "/jobs/999999",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/jobs" in response.headers["Location"]


def test_nonexistent_job_shows_message(
    client,
):
    response = client.get(
        "/jobs/999999",
        follow_redirects=True,
    )

    assert response.status_code == 200

    page_text = response.get_data(as_text=True).lower()

    assert "requested job was not found" in page_text


def test_job_keyword_search(
    client,
    app,
):
    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
    )

    response = client.get(
        "/jobs",
        query_string={
            "keyword": ("Junior Software Engineer"),
        },
    )

    assert response.status_code == 200
    assert b"Junior Software Engineer" in response.data


def test_job_location_filter(
    client,
    app,
):
    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
    )

    response = client.get(
        "/jobs",
        query_string={
            "location": "Kuala Lumpur",
        },
    )

    assert response.status_code == 200
    assert b"Junior Software Engineer" in response.data


def test_job_category_filter(
    client,
    app,
):
    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
    )

    response = client.get(
        "/jobs",
        query_string={
            "category": "Development",
        },
    )

    assert response.status_code == 200
    assert b"Junior Software Engineer" in response.data


def test_invalid_page_number_does_not_crash(
    client,
):
    response = client.get(
        "/jobs",
        query_string={
            "page": "invalid",
        },
    )

    assert response.status_code == 200


def test_negative_page_number_does_not_crash(
    client,
):
    response = client.get(
        "/jobs",
        query_string={
            "page": "-10",
        },
    )

    assert response.status_code == 200


def test_invalid_sort_option_does_not_crash(
    client,
):
    response = client.get(
        "/jobs",
        query_string={
            "sort": "invalid-sort",
        },
    )

    assert response.status_code == 200


def test_save_job_without_login_redirects(
    client,
    app,
):
    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
    )

    response = client.post(
        f"/jobs/{job_id}/save",
        follow_redirects=False,
    )

    assert response.status_code == 302

    location = response.headers["Location"]

    assert "/seeker-profile" in location


def test_logged_in_seeker_can_save_job(
    client,
    app,
):
    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
    )

    seeker_id = create_seeker(app)

    login_seeker(
        client,
        seeker_id,
    )

    response = client.post(
        f"/jobs/{job_id}/save",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        connection = get_db_connection()

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

        connection.close()

    assert saved_job is not None


def test_seeker_can_remove_saved_job(
    client,
    app,
):
    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
    )

    seeker_id = create_seeker(app)

    login_seeker(
        client,
        seeker_id,
    )

    client.post(
        f"/jobs/{job_id}/save",
        follow_redirects=False,
    )

    response = client.post(
        f"/jobs/{job_id}/save",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        connection = get_db_connection()

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

        connection.close()

    assert saved_job is None
