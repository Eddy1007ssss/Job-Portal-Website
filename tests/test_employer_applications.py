from src.database import get_db_connection
from werkzeug.security import generate_password_hash


def normalize_html(response) -> str:
    """
    Convert rendered HTML into normalized text.

    This removes repeated spaces and line breaks so that tests are
    not affected by HTML formatting.
    """

    return " ".join(
        response.get_data(as_text=True).split()
    )


def create_employer(
    app,
    email="employer@example.com",
    company_name="ABC Technology",
):
    """Create a test employer and return the employer ID."""

    with app.app_context():
        connection = get_db_connection()

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
                email,
                "0123456789",
                generate_password_hash("Password123"),
            ),
        )

        employer_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

    return employer_id


def create_seeker(
    app,
    email="candidate@example.com",
    full_name="Ali Candidate",
    contact_number="0198765432",
    job_title="Software Developer",
    location="Kuala Lumpur",
    about_me="A motivated software developer.",
    resume_filename="ali_resume.pdf",
):
    """Create a test seeker and seeker profile."""

    with app.app_context():
        connection = get_db_connection()

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
                full_name,
                email,
                contact_number,
                generate_password_hash("Password123"),
            ),
        )

        seeker_id = int(cursor.lastrowid)

        connection.execute(
            """
            INSERT INTO seeker_profiles (
                seeker_id,
                job_title,
                location,
                about_me,
                resume_filename
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                seeker_id,
                job_title,
                location,
                about_me,
                resume_filename,
            ),
        )

        connection.commit()
        connection.close()

    return seeker_id


def create_job(
    app,
    employer_id,
    title="Software Engineer",
    location="Kuala Lumpur",
    employment_type="Full-time",
    status="Open",
):
    """Create a test job and return the job ID."""

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
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                employer_id,
                title,
                "Develop and maintain software applications.",
                location,
                employment_type,
                status,
            ),
        )

        job_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

    return job_id


def create_application(
    app,
    seeker_id,
    job_id,
    status="Pending",
    cover_letter="I am interested in this position.",
    resume_filename="application_resume.pdf",
    applied_at=None,
):
    """Create a test application and return the application ID."""

    with app.app_context():
        connection = get_db_connection()

        if applied_at is None:
            cursor = connection.execute(
                """
                INSERT INTO applications (
                    seeker_id,
                    job_id,
                    cover_letter,
                    resume_filename,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    seeker_id,
                    job_id,
                    cover_letter,
                    resume_filename,
                    status,
                ),
            )
        else:
            cursor = connection.execute(
                """
                INSERT INTO applications (
                    seeker_id,
                    job_id,
                    cover_letter,
                    resume_filename,
                    status,
                    applied_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    seeker_id,
                    job_id,
                    cover_letter,
                    resume_filename,
                    status,
                    applied_at,
                ),
            )

        application_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

    return application_id


def login_employer(
    client,
    employer_id,
    company_name="ABC Technology",
    email="employer@example.com",
):
    """Create an employer login session for testing."""

    with client.session_transaction() as session:
        session["employer_id"] = employer_id
        session["employer_company_name"] = company_name
        session["employer_email"] = email


# =========================================================
# Application list tests
# =========================================================


def test_application_list_requires_employer_login(client):
    """Unauthenticated users must be redirected to employer login."""

    response = client.get(
        "/employer/jobs/1/applications",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/employer/login" in response.headers["Location"]


def test_employer_can_view_applications_for_own_job(
    client,
    app,
):
    """An employer can view applications for their own job."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Ali Candidate" in page_text
    assert "Software Engineer" in page_text
    assert "Pending" in page_text
    assert "Available" in page_text


def test_application_list_displays_empty_state(
    client,
    app,
):
    """A job without applications displays an empty-state message."""

    employer_id = create_employer(app)
    job_id = create_job(app, employer_id)

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "No applications yet" in page_text
    assert (
        "Candidates who apply for this job posting will appear here."
        in page_text
    )


def test_employer_cannot_view_another_employers_job_applications(
    client,
    app,
):
    """An employer cannot view another employer's applications."""

    first_employer_id = create_employer(
        app,
        email="first@example.com",
        company_name="First Company",
    )

    second_employer_id = create_employer(
        app,
        email="second@example.com",
        company_name="Second Company",
    )

    second_job_id = create_job(
        app,
        second_employer_id,
    )

    login_employer(
        client,
        first_employer_id,
        company_name="First Company",
        email="first@example.com",
    )

    response = client.get(
        f"/employer/jobs/{second_job_id}/applications",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/employer/jobs" in response.headers["Location"]


def test_application_list_orders_newest_first(
    client,
    app,
):
    """The latest application appears before older applications."""

    employer_id = create_employer(app)

    first_seeker_id = create_seeker(
        app,
        email="first.candidate@example.com",
        full_name="First Candidate",
    )

    second_seeker_id = create_seeker(
        app,
        email="second.candidate@example.com",
        full_name="Second Candidate",
    )

    job_id = create_job(app, employer_id)

    create_application(
        app,
        first_seeker_id,
        job_id,
        applied_at="2026-07-01 10:00:00",
    )

    create_application(
        app,
        second_seeker_id,
        job_id,
        applied_at="2026-07-02 10:00:00",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert page_text.index(
        "second.candidate@example.com"
    ) < page_text.index(
        "first.candidate@example.com"
    )


def test_application_list_displays_view_applicant_button(
    client,
    app,
):
    """The application list contains the View Applicant button."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "View Applicant" in page_text
    assert (
        f"/employer/applications/{application_id}"
        in page_text
    )


def test_application_list_displays_resume_available(
    client,
    app,
):
    """The application list displays Available when a resume exists."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
        resume_filename="candidate_resume.pdf",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Available" in page_text


def test_application_list_displays_resume_unavailable(
    client,
    app,
):
    """The application list displays Not available without a resume."""

    employer_id = create_employer(app)

    seeker_id = create_seeker(
        app,
        resume_filename=None,
    )

    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
        resume_filename=None,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Not available" in page_text


def test_application_list_displays_pending_status(
    client,
    app,
):
    """The application list displays a Pending status."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
        status="Pending",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200
    assert "Pending" in normalize_html(response)


def test_application_list_displays_reviewing_status(
    client,
    app,
):
    """The application list displays a Reviewing status."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
        status="Reviewing",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200
    assert "Reviewing" in normalize_html(response)


def test_application_list_displays_shortlisted_status(
    client,
    app,
):
    """The application list displays a Shortlisted status."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
        status="Shortlisted",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200
    assert "Shortlisted" in normalize_html(response)


def test_application_list_displays_accepted_status(
    client,
    app,
):
    """The application list displays an Accepted status."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
        status="Accepted",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200
    assert "Accepted" in normalize_html(response)


def test_application_list_displays_rejected_status(
    client,
    app,
):
    """The application list displays a Rejected status."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    create_application(
        app,
        seeker_id,
        job_id,
        status="Rejected",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200
    assert "Rejected" in normalize_html(response)


def test_application_list_displays_multiple_candidates(
    client,
    app,
):
    """The employer can see multiple candidates for one job."""

    employer_id = create_employer(app)

    first_seeker_id = create_seeker(
        app,
        email="candidate.one@example.com",
        full_name="Candidate One",
    )

    second_seeker_id = create_seeker(
        app,
        email="candidate.two@example.com",
        full_name="Candidate Two",
    )

    job_id = create_job(app, employer_id)

    create_application(
        app,
        first_seeker_id,
        job_id,
    )

    create_application(
        app,
        second_seeker_id,
        job_id,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/jobs/{job_id}/applications"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Candidate One" in page_text
    assert "Candidate Two" in page_text
    assert "candidate.one@example.com" in page_text
    assert "candidate.two@example.com" in page_text


# =========================================================
# Applicant details tests
# =========================================================


def test_application_details_requires_employer_login(
    client,
    app,
):
    """Unauthenticated users cannot view applicant details."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    response = client.get(
        f"/employer/applications/{application_id}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/employer/login" in response.headers["Location"]


def test_employer_can_view_applicant_details(
    client,
    app,
):
    """An employer can view an applicant for their own job."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Ali Candidate" in page_text
    assert "candidate@example.com" in page_text
    assert "I am interested in this position." in page_text


def test_application_details_displays_profile_information(
    client,
    app,
):
    """Applicant profile details are displayed."""

    employer_id = create_employer(app)

    seeker_id = create_seeker(
        app,
        job_title="Python Developer",
        location="Selangor",
        about_me="I enjoy developing Flask applications.",
    )

    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Python Developer" in page_text
    assert "Selangor" in page_text
    assert "I enjoy developing Flask applications." in page_text


def test_application_details_displays_contact_information(
    client,
    app,
):
    """Applicant email and contact number are displayed."""

    employer_id = create_employer(app)

    seeker_id = create_seeker(
        app,
        email="contact@example.com",
        contact_number="01122334455",
    )

    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "contact@example.com" in page_text
    assert "01122334455" in page_text


def test_application_details_displays_cover_letter(
    client,
    app,
):
    """The applicant's cover letter is displayed."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    cover_letter = (
        "I have three years of software development experience."
    )

    application_id = create_application(
        app,
        seeker_id,
        job_id,
        cover_letter=cover_letter,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200
    assert cover_letter in normalize_html(response)


def test_application_details_displays_no_cover_letter_message(
    client,
    app,
):
    """A missing cover letter displays a suitable message."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)
    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
        cover_letter=None,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "No cover letter was submitted." in page_text


def test_application_details_uses_application_resume_first(
    client,
    app,
):
    """An application resume has priority over a profile resume."""

    employer_id = create_employer(app)

    seeker_id = create_seeker(
        app,
        resume_filename="profile_resume.pdf",
    )

    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
        resume_filename="application_resume.pdf",
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "application_resume.pdf" in page_text
    assert "View Resume" in page_text
    assert "Download Resume" in page_text


def test_application_details_uses_profile_resume_as_fallback(
    client,
    app,
):
    """The profile resume is used when no application resume exists."""

    employer_id = create_employer(app)

    seeker_id = create_seeker(
        app,
        resume_filename="profile_resume.pdf",
    )

    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
        resume_filename=None,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "profile_resume.pdf" in page_text
    assert "View Resume" in page_text


def test_application_details_displays_no_resume_message(
    client,
    app,
):
    """A suitable message is displayed when no resume exists."""

    employer_id = create_employer(app)

    seeker_id = create_seeker(
        app,
        resume_filename=None,
    )

    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
        resume_filename=None,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "No resume available." in page_text


def test_application_details_handles_missing_profile_fields(
    client,
    app,
):
    """Missing optional profile fields do not break the page."""

    employer_id = create_employer(app)

    seeker_id = create_seeker(
        app,
        contact_number=None,
        job_title=None,
        location=None,
        about_me=None,
        resume_filename=None,
    )

    job_id = create_job(app, employer_id)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
        cover_letter=None,
        resume_filename=None,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Job Seeker" in page_text
    assert "Not provided" in page_text
    assert (
        "The applicant has not added an introduction."
        in page_text
    )


def test_employer_cannot_view_another_employers_applicant_details(
    client,
    app,
):
    """An employer cannot access another employer's applicant."""

    first_employer_id = create_employer(
        app,
        email="first@example.com",
        company_name="First Company",
    )

    second_employer_id = create_employer(
        app,
        email="second@example.com",
        company_name="Second Company",
    )

    seeker_id = create_seeker(app)

    second_job_id = create_job(
        app,
        second_employer_id,
    )

    application_id = create_application(
        app,
        seeker_id,
        second_job_id,
    )

    login_employer(
        client,
        first_employer_id,
        company_name="First Company",
        email="first@example.com",
    )

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 404


def test_employer_cannot_view_nonexistent_application(
    client,
    app,
):
    """A nonexistent application returns 404."""

    employer_id = create_employer(app)

    login_employer(client, employer_id)

    response = client.get(
        "/employer/applications/999999"
    )

    assert response.status_code == 404


def test_application_details_displays_job_information(
    client,
    app,
):
    """The details page displays the applied job information."""

    employer_id = create_employer(app)
    seeker_id = create_seeker(app)

    job_id = create_job(
        app,
        employer_id,
        title="Backend Developer",
        location="Penang",
    )

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(client, employer_id)

    response = client.get(
        f"/employer/applications/{application_id}"
    )

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Backend Developer" in page_text
    assert "Penang" in page_text