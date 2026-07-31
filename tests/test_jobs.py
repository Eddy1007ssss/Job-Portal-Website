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
    with client.session_transaction() as current_session:
        current_session["seeker_id"] = seeker_id
        current_session["seeker_authenticated"] = True


def test_job_list_page_loads(client, app):
    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

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

    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

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

    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    assert b"Junior Software Engineer" in response.data
    assert b"Kuala Lumpur" in response.data


def test_nonexistent_job_redirects_to_job_list(
    client,
    app,
):
    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

    response = client.get(
        "/jobs/999999",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/jobs" in response.headers["Location"]


def test_nonexistent_job_shows_message(
    client,
    app,
):
    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

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

    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

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

    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

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

    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

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
    app,
):
    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

    response = client.get(
        "/jobs",
        query_string={
            "page": "invalid",
        },
    )

    assert response.status_code == 200


def test_negative_page_number_does_not_crash(
    client,
    app,
):
    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

    response = client.get(
        "/jobs",
        query_string={
            "page": "-10",
        },
    )

    assert response.status_code == 200


def test_invalid_sort_option_does_not_crash(
    client,
    app,
):
    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)

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


# =========================================================
# Cover letter application tests
# =========================================================


VALID_COVER_LETTER = (
    "I am excited to apply for this role because my software development "
    "experience and teamwork skills match the job requirements."
)


def get_application(app, seeker_id, job_id):
    with app.app_context():
        connection = get_db_connection()
        application = connection.execute(
            """
            SELECT application_id, cover_letter, status
            FROM applications
            WHERE seeker_id = ?
              AND job_id = ?
            """,
            (
                seeker_id,
                job_id,
            ),
        ).fetchone()
        connection.close()

    return application


def create_application_context(app, client):
    employer_id = create_employer(app)
    job_id = create_job(app, employer_id)
    seeker_id = create_seeker(app)
    login_seeker(client, seeker_id)
    return employer_id, seeker_id, job_id


def test_job_details_displays_cover_letter_form(client, app):
    _, _, job_id = create_application_context(app, client)

    response = client.get(f"/jobs/{job_id}")
    page_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="cover_letter"' in page_text
    assert 'minlength="50"' in page_text
    assert 'maxlength="2000"' in page_text
    assert "Submit Application" in page_text


def test_valid_cover_letter_is_saved_with_application(client, app):
    _, seeker_id, job_id = create_application_context(app, client)

    response = client.post(
        f"/applications/jobs/{job_id}/apply",
        data={"cover_letter": VALID_COVER_LETTER},
        follow_redirects=False,
    )

    application = get_application(app, seeker_id, job_id)
    assert response.status_code == 302
    assert application is not None
    assert application["cover_letter"] == VALID_COVER_LETTER
    assert application["status"] == "Pending"


def test_cover_letter_is_trimmed_before_saving(client, app):
    _, seeker_id, job_id = create_application_context(app, client)

    client.post(
        f"/applications/jobs/{job_id}/apply",
        data={"cover_letter": f"  {VALID_COVER_LETTER}  "},
    )

    application = get_application(app, seeker_id, job_id)
    assert application is not None
    assert application["cover_letter"] == VALID_COVER_LETTER


def test_missing_cover_letter_is_rejected(client, app):
    _, seeker_id, job_id = create_application_context(app, client)

    response = client.post(
        f"/applications/jobs/{job_id}/apply",
        data={"cover_letter": ""},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert get_application(app, seeker_id, job_id) is None
    assert b"Please write a cover letter before applying." in response.data


def test_short_cover_letter_is_rejected(client, app):
    _, seeker_id, job_id = create_application_context(app, client)

    response = client.post(
        f"/applications/jobs/{job_id}/apply",
        data={"cover_letter": "Too short."},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert get_application(app, seeker_id, job_id) is None
    assert b"Cover letter must contain at least 50 characters." in response.data


def test_long_cover_letter_is_rejected(client, app):
    _, seeker_id, job_id = create_application_context(app, client)

    response = client.post(
        f"/applications/jobs/{job_id}/apply",
        data={"cover_letter": "A" * 2001},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert get_application(app, seeker_id, job_id) is None
    assert b"Cover letter must not exceed 2000 characters." in response.data


def test_guest_cannot_submit_cover_letter(client, app):
    employer_id = create_employer(app)
    job_id = create_job(app, employer_id)

    response = client.post(
        f"/applications/jobs/{job_id}/apply",
        data={"cover_letter": VALID_COVER_LETTER},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        connection = get_db_connection()
        application_count = connection.execute(
            "SELECT COUNT(*) FROM applications WHERE job_id = ?",
            (job_id,),
        ).fetchone()[0]
        connection.close()
    assert application_count == 0


def test_employer_can_view_submitted_cover_letter(client, app):
    employer_id, _, job_id = create_application_context(app, client)

    client.post(
        f"/applications/jobs/{job_id}/apply",
        data={"cover_letter": VALID_COVER_LETTER},
    )

    with app.app_context():
        connection = get_db_connection()
        application_id = connection.execute(
            "SELECT application_id FROM applications WHERE job_id = ?",
            (job_id,),
        ).fetchone()["application_id"]
        connection.close()

    with client.session_transaction() as current_session:
        current_session.clear()
        current_session["employer_id"] = employer_id

    response = client.get(f"/employer/applications/{application_id}")

    assert response.status_code == 200
    assert VALID_COVER_LETTER in response.get_data(as_text=True)
