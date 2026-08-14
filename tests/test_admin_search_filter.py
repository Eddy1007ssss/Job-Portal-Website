from werkzeug.security import generate_password_hash

from src.admin import get_jobs_for_moderation, get_registered_users
from src.database import get_db_connection


def insert_search_records(app) -> dict[str, int]:
    with app.app_context():
        connection = get_db_connection()
        admin_cursor = connection.execute(
            """
            INSERT INTO admins (
                full_name,
                email,
                password_hash,
                role,
                is_active
            )
            VALUES (?, ?, ?, 'admin', 1)
            """,
            (
                "Search Admin",
                "search-admin@example.com",
                generate_password_hash("password123"),
            ),
        )
        employer_cursor = connection.execute(
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
                "Blue Ocean Technology",
                "contact@blueocean.example",
                "03-2222-3333",
                generate_password_hash("password123"),
            ),
        )
        second_employer_cursor = connection.execute(
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
                "Northern Design Studio",
                "hello@northern.example",
                "04-5555-6666",
                generate_password_hash("password123"),
            ),
        )
        connection.execute(
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
                "Alicia Tan",
                "alicia@example.com",
                "012-987-6543",
                generate_password_hash("password123"),
            ),
        )
        assert admin_cursor.lastrowid is not None
        assert employer_cursor.lastrowid is not None
        assert second_employer_cursor.lastrowid is not None
        admin_id = int(admin_cursor.lastrowid)
        employer_id = int(employer_cursor.lastrowid)
        second_employer_id = int(second_employer_cursor.lastrowid)

        connection.execute(
            """
            INSERT INTO jobs (
                employer_id,
                title,
                description,
                location,
                employment_type,
                category,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Open')
            """,
            (
                employer_id,
                "Python Backend Engineer",
                "Build secure Flask APIs.",
                "Kuala Lumpur",
                "Full-time",
                "Development",
            ),
        )
        connection.execute(
            """
            INSERT INTO jobs (
                employer_id,
                title,
                description,
                location,
                employment_type,
                category,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Closed')
            """,
            (
                second_employer_id,
                "Product Designer",
                "Create accessible interface prototypes.",
                "Penang",
                "Contract",
                "Design",
            ),
        )
        connection.commit()
        connection.close()

    return {"admin_id": admin_id}


def login_admin(client, record_ids: dict[str, int]) -> None:
    with client.session_transaction() as admin_session:
        admin_session["admin_id"] = record_ids["admin_id"]
        admin_session["admin_name"] = "Search Admin"
        admin_session["admin_email"] = "search-admin@example.com"
        admin_session["admin_role"] = "admin"
        admin_session["admin_authenticated"] = True


def test_user_search_matches_name_email_and_phone(app):
    insert_search_records(app)

    with app.app_context():
        connection = get_db_connection()
        name_results = get_registered_users(connection, search="alicia")
        email_results = get_registered_users(connection, search="BLUEOCEAN")
        phone_results = get_registered_users(connection, search="987-6543")
        connection.close()

    assert [row["display_name"] for row in name_results.users] == ["Alicia Tan"]
    assert [row["display_name"] for row in email_results.users] == [
        "Blue Ocean Technology"
    ]
    assert [row["display_name"] for row in phone_results.users] == ["Alicia Tan"]


def test_user_type_filter_combines_with_search(app):
    insert_search_records(app)

    with app.app_context():
        connection = get_db_connection()
        employer_results = get_registered_users(
            connection,
            account_type="employer",
            search="Design",
        )
        seeker_results = get_registered_users(
            connection,
            account_type="seeker",
            search="Design",
        )
        connection.close()

    assert [row["display_name"] for row in employer_results.users] == [
        "Northern Design Studio"
    ]
    assert seeker_results.users == []


def test_job_search_matches_title_company_category_location_and_description(app):
    insert_search_records(app)

    with app.app_context():
        connection = get_db_connection()
        title_results = get_jobs_for_moderation(connection, search="Python")
        company_results = get_jobs_for_moderation(connection, search="Northern")
        category_results = get_jobs_for_moderation(connection, search="Development")
        location_results = get_jobs_for_moderation(connection, search="Penang")
        description_results = get_jobs_for_moderation(connection, search="Flask")
        connection.close()

    assert [row["title"] for row in title_results.jobs] == ["Python Backend Engineer"]
    assert [row["title"] for row in company_results.jobs] == ["Product Designer"]
    assert [row["title"] for row in category_results.jobs] == [
        "Python Backend Engineer"
    ]
    assert [row["title"] for row in location_results.jobs] == ["Product Designer"]
    assert [row["title"] for row in description_results.jobs] == [
        "Python Backend Engineer"
    ]


def test_job_status_filter_combines_with_search(app):
    insert_search_records(app)

    with app.app_context():
        connection = get_db_connection()
        matching_results = get_jobs_for_moderation(
            connection,
            status="closed",
            search="Designer",
        )
        no_results = get_jobs_for_moderation(
            connection,
            status="open",
            search="Designer",
        )
        connection.close()

    assert [row["title"] for row in matching_results.jobs] == ["Product Designer"]
    assert no_results.jobs == []


def test_admin_pages_display_matching_results_and_empty_state(app, client):
    record_ids = insert_search_records(app)
    login_admin(client, record_ids)

    user_response = client.get("/admin/users?type=seeker&search=Alicia")
    job_response = client.get("/admin/jobs?status=closed&search=Designer")
    empty_response = client.get("/admin/jobs?search=NoSuchVacancy")

    assert user_response.status_code == 200
    assert b"Alicia Tan" in user_response.data
    assert b"Blue Ocean Technology" not in user_response.data

    assert job_response.status_code == 200
    assert b"Product Designer" in job_response.data
    assert b"Python Backend Engineer" not in job_response.data

    assert empty_response.status_code == 200
    assert b"No job postings found" in empty_response.data
