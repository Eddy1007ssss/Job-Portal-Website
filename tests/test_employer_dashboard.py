from werkzeug.security import generate_password_hash

from src.database import get_db_connection

# =========================================================
# Test helper functions
# =========================================================


def create_employer(
    app,
    email="dashboard@example.com",
    company_name="Dashboard Technology",
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


def login_employer(
    client,
    employer_id,
    company_name="Dashboard Technology",
    email="dashboard@example.com",
):
    """Create an employer login session."""

    with client.session_transaction() as session:
        session["employer_id"] = employer_id
        session["employer_company_name"] = company_name
        session["employer_email"] = email


def create_job(
    app,
    employer_id,
    title="Software Engineer",
    status="Open",
    location="Kuala Lumpur",
    employment_type="Full-time",
):
    """Create a job posting and return the job ID."""

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
                "Test job description.",
                location,
                employment_type,
                status,
            ),
        )

        job_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

    return job_id


def create_seeker(
    app,
    email="candidate.dashboard@example.com",
    full_name="Dashboard Candidate",
):
    """Create a job seeker and return the seeker ID."""

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
                "0198765432",
                generate_password_hash("Password123"),
            ),
        )

        seeker_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

    return seeker_id


def create_application(
    app,
    seeker_id,
    job_id,
    status="Pending",
    applied_at=None,
):
    """Create an application and return its ID."""

    with app.app_context():
        connection = get_db_connection()

        if applied_at is None:
            cursor = connection.execute(
                """
                INSERT INTO applications (
                    seeker_id,
                    job_id,
                    cover_letter,
                    status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    seeker_id,
                    job_id,
                    "Dashboard test application.",
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
                    status,
                    applied_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    seeker_id,
                    job_id,
                    "Dashboard test application.",
                    status,
                    applied_at,
                ),
            )

        application_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

    return application_id


def normalize_html(response):
    """Remove extra HTML whitespace for easier assertions."""

    return " ".join(response.get_data(as_text=True).split())


# =========================================================
# Employer dashboard access tests
# =========================================================


def test_dashboard_requires_employer_login(
    client,
):
    """Employer dashboard must require login."""

    response = client.get(
        "/employer/dashboard",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/employer/login" in response.headers["Location"]


def test_employer_dashboard_loads(
    client,
    app,
):
    """Logged-in employer can open dashboard."""

    employer_id = create_employer(app)

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Employer Dashboard" in page_text
    assert "Dashboard Technology" in page_text


# =========================================================
# Dashboard statistics tests
# =========================================================


def test_dashboard_displays_total_job_postings(
    client,
    app,
):
    """Dashboard displays total number of employer jobs."""

    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
        title="Developer",
        status="Open",
    )

    create_job(
        app,
        employer_id,
        title="Designer",
        status="Closed",
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Total Job Postings" in page_text
    assert "2" in page_text


def test_dashboard_displays_active_vacancies(
    client,
    app,
):
    """Dashboard displays active vacancy count."""

    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
        title="Developer",
        status="Open",
    )

    create_job(
        app,
        employer_id,
        title="Designer",
        status="Open",
    )

    create_job(
        app,
        employer_id,
        title="Manager",
        status="Closed",
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Active Vacancies" in page_text
    assert "2" in page_text


def test_dashboard_displays_closed_vacancies(
    client,
    app,
):
    """Dashboard displays closed vacancy count."""

    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
        title="Developer",
        status="Closed",
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Closed Vacancies" in page_text
    assert "1" in page_text


def test_dashboard_displays_total_applications(
    client,
    app,
):
    """Dashboard displays total applications received."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="Software Engineer",
        status="Open",
    )

    seeker_id = create_seeker(app)

    create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Applications Received" in page_text
    assert "1" in page_text


def test_dashboard_counts_multiple_applications(
    client,
    app,
):
    """Dashboard correctly counts multiple applications."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="Software Engineer",
        status="Open",
    )

    first_seeker = create_seeker(
        app,
        email="first.dashboard@example.com",
        full_name="First Candidate",
    )

    second_seeker = create_seeker(
        app,
        email="second.dashboard@example.com",
        full_name="Second Candidate",
    )

    create_application(
        app,
        first_seeker,
        job_id,
    )

    create_application(
        app,
        second_seeker,
        job_id,
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Applications Received" in page_text
    assert "2" in page_text


def test_dashboard_does_not_count_other_employer_jobs(
    client,
    app,
):
    """Employer dashboard only includes employer-owned jobs."""

    first_employer = create_employer(
        app,
        email="first-dashboard@example.com",
        company_name="First Company",
    )

    second_employer = create_employer(
        app,
        email="second-dashboard@example.com",
        company_name="Second Company",
    )

    create_job(
        app,
        first_employer,
        title="First Job",
        status="Open",
    )

    create_job(
        app,
        second_employer,
        title="Second Job",
        status="Open",
    )

    login_employer(
        client,
        first_employer,
        company_name="First Company",
        email="first-dashboard@example.com",
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "First Job" in page_text
    assert "Second Job" not in page_text


def test_dashboard_does_not_count_other_employer_applications(
    client,
    app,
):
    """Applications for another employer must not be counted."""

    first_employer = create_employer(
        app,
        email="first-app@example.com",
        company_name="First Company",
    )

    second_employer = create_employer(
        app,
        email="second-app@example.com",
        company_name="Second Company",
    )

    first_job = create_job(
        app,
        first_employer,
        title="First Company Job",
        status="Open",
    )

    second_job = create_job(
        app,
        second_employer,
        title="Second Company Job",
        status="Open",
    )

    first_seeker = create_seeker(
        app,
        email="first.application@example.com",
        full_name="First Applicant",
    )

    second_seeker = create_seeker(
        app,
        email="second.application@example.com",
        full_name="Second Applicant",
    )

    create_application(
        app,
        first_seeker,
        first_job,
    )

    create_application(
        app,
        second_seeker,
        second_job,
    )

    login_employer(
        client,
        first_employer,
        company_name="First Company",
        email="first-app@example.com",
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "First Applicant" in page_text
    assert "Second Applicant" not in page_text


# =========================================================
# Recent job posting tests
# =========================================================


def test_dashboard_displays_recent_job(
    client,
    app,
):
    """Recently posted job appears on the dashboard."""

    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
        title="Junior Software Developer",
        status="Open",
        location="Penang, Malaysia",
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Recent Job Postings" in page_text
    assert "Junior Software Developer" in page_text
    assert "Penang, Malaysia" in page_text


def test_dashboard_empty_state(
    client,
    app,
):
    """Dashboard displays empty state when employer has no jobs."""

    employer_id = create_employer(app)

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "No job postings yet" in page_text


# =========================================================
# Recent applicant tests
# =========================================================


def test_dashboard_displays_recent_applicant(
    client,
    app,
):
    """Recent applicant appears on employer dashboard."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="Software Developer",
        status="Open",
    )

    seeker_id = create_seeker(app)

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Recent Applicants" in page_text
    assert "Dashboard Candidate" in page_text
    assert "Software Developer" in page_text
    assert "View Applicant" in page_text
    assert f"/employer/applications/{application_id}" in page_text


def test_dashboard_recent_applicants_empty_state(
    client,
    app,
):
    """Dashboard displays empty state when no applications exist."""

    employer_id = create_employer(app)

    create_job(
        app,
        employer_id,
        title="Software Developer",
        status="Open",
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert "Recent Applicants" in page_text
    assert "No recent applicants" in page_text


def test_dashboard_recent_applicant_displays_job_title(
    client,
    app,
):
    """Recent applicant section displays applied job title."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="Backend Developer",
        status="Open",
    )

    seeker_id = create_seeker(
        app,
        full_name="Backend Candidate",
    )

    create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Backend Candidate" in page_text
    assert "Backend Developer" in page_text


def test_dashboard_recent_applicant_displays_application_date(
    client,
    app,
):
    """Recent applicant section displays application date."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="Frontend Developer",
        status="Open",
    )

    seeker_id = create_seeker(
        app,
        full_name="Frontend Candidate",
    )

    create_application(
        app,
        seeker_id,
        job_id,
        applied_at="2026-08-12 10:30:00",
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "Frontend Candidate" in page_text
    assert "2026-08-12 10:30:00" in page_text


def test_dashboard_recent_applicants_newest_first(
    client,
    app,
):
    """Newest submitted application appears first."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="Backend Developer",
        status="Open",
    )

    older_seeker_id = create_seeker(
        app,
        email="older@example.com",
        full_name="Older Candidate",
    )

    newest_seeker_id = create_seeker(
        app,
        email="newest@example.com",
        full_name="Newest Candidate",
    )

    create_application(
        app,
        older_seeker_id,
        job_id,
        applied_at="2026-08-10 09:00:00",
    )

    create_application(
        app,
        newest_seeker_id,
        job_id,
        applied_at="2026-08-12 09:00:00",
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    assert response.status_code == 200

    page_text = normalize_html(response)

    assert page_text.index("Newest Candidate") < page_text.index("Older Candidate")


def test_dashboard_recent_applicants_only_show_logged_in_employer(
    client,
    app,
):
    """Recent applicants must belong to the logged-in employer."""

    first_employer = create_employer(
        app,
        email="recent-first@example.com",
        company_name="Recent First Company",
    )

    second_employer = create_employer(
        app,
        email="recent-second@example.com",
        company_name="Recent Second Company",
    )

    first_job = create_job(
        app,
        first_employer,
        title="First Employer Job",
        status="Open",
    )

    second_job = create_job(
        app,
        second_employer,
        title="Second Employer Job",
        status="Open",
    )

    first_seeker = create_seeker(
        app,
        email="first-recent@example.com",
        full_name="First Recent Applicant",
    )

    second_seeker = create_seeker(
        app,
        email="second-recent@example.com",
        full_name="Second Recent Applicant",
    )

    create_application(
        app,
        first_seeker,
        first_job,
    )

    create_application(
        app,
        second_seeker,
        second_job,
    )

    login_employer(
        client,
        first_employer,
        company_name="Recent First Company",
        email="recent-first@example.com",
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "First Recent Applicant" in page_text
    assert "Second Recent Applicant" not in page_text


def test_dashboard_recent_applicants_limit_five(
    client,
    app,
):
    """Dashboard displays at most five recent applicants."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="Software Developer",
        status="Open",
    )

    for number in range(1, 7):
        seeker_id = create_seeker(
            app,
            email=f"candidate{number}@example.com",
            full_name=f"Candidate {number}",
        )

        create_application(
            app,
            seeker_id,
            job_id,
            applied_at=(f"2026-08-{number + 5:02d} " "10:00:00"),
        )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200

    assert "Candidate 6" in page_text
    assert "Candidate 5" in page_text
    assert "Candidate 4" in page_text
    assert "Candidate 3" in page_text
    assert "Candidate 2" in page_text

    # Oldest applicant should not appear because LIMIT is 5.
    assert "Candidate 1" not in page_text


def test_dashboard_recent_applicant_view_link(
    client,
    app,
):
    """View Applicant button links to applicant details page."""

    employer_id = create_employer(app)

    job_id = create_job(
        app,
        employer_id,
        title="QA Engineer",
        status="Open",
    )

    seeker_id = create_seeker(
        app,
        full_name="QA Candidate",
    )

    application_id = create_application(
        app,
        seeker_id,
        job_id,
    )

    login_employer(
        client,
        employer_id,
    )

    response = client.get("/employer/dashboard")

    page_text = normalize_html(response)

    assert response.status_code == 200
    assert "View Applicant" in page_text
    assert f"/employer/applications/{application_id}" in page_text
