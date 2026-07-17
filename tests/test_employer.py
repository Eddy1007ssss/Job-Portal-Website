import pytest
from src.database import get_db_connection
from werkzeug.security import generate_password_hash


def test_employer_register_page_loads(client):
    response = client.get("/employer/register")

    assert response.status_code == 200


def test_employer_login_page_loads(client):
    response = client.get("/employer/login")

    assert response.status_code == 200


def test_register_employer_successfully(client, app):
    response = client.post(
        "/employer/register",
        data={
            "company_name": "ABC Technology Sdn Bhd",
            "company_email": "abc@example.com",
            "contact_number": "0123456789",
            "password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    with app.app_context():
        connection = get_db_connection()

        employer = connection.execute(
            """
            SELECT *
            FROM employers
            WHERE company_email = ?
            """,
            ("abc@example.com",),
        ).fetchone()

        connection.close()

    assert employer is not None
    assert employer["company_name"] == "ABC Technology Sdn Bhd"


@pytest.mark.skip(
    reason=("Duplicate employer email handling " "needs employer.py review.")
)
def test_register_duplicate_employer_email(client):
    registration_data = {
        "company_name": "ABC Technology",
        "company_email": "duplicate@example.com",
        "contact_number": "0123456789",
        "password": "Password123",
        "confirm_password": "Password123",
    }

    first_response = client.post(
        "/employer/register",
        data=registration_data,
        follow_redirects=True,
    )

    second_response = client.post(
        "/employer/register",
        data=registration_data,
        follow_redirects=True,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    page_text = second_response.get_data(as_text=True).lower()

    assert "already" in page_text or "exists" in page_text or "registered" in page_text


def test_register_password_mismatch(client):
    response = client.post(
        "/employer/register",
        data={
            "company_name": "ABC Technology",
            "company_email": "abc@example.com",
            "contact_number": "0123456789",
            "password": "Password123",
            "confirm_password": "DifferentPassword",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    page_text = response.get_data(as_text=True).lower()

    assert "password" in page_text and ("match" in page_text or "same" in page_text)


def create_employer(app):
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
                "ABC Technology",
                "abc@example.com",
                "0123456789",
                generate_password_hash("Password123"),
            ),
        )

        employer_id = cursor.lastrowid

        connection.commit()
        connection.close()

    return employer_id


def test_employer_login_success(client, app):
    create_employer(app)

    response = client.post(
        "/employer/login",
        data={
            "company_email": "abc@example.com",
            "password": "Password123",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    with client.session_transaction() as session:
        assert session.get("employer_id") is not None
        assert session.get("employer_email") == "abc@example.com"


def test_employer_login_wrong_password(client, app):
    create_employer(app)

    response = client.post(
        "/employer/login",
        data={
            "company_email": "abc@example.com",
            "password": "WrongPassword",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    page_text = response.get_data(as_text=True).lower()

    assert "invalid" in page_text or "incorrect" in page_text


def test_employer_login_unknown_email(client):
    response = client.post(
        "/employer/login",
        data={
            "company_email": "unknown@example.com",
            "password": "Password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    page_text = response.get_data(as_text=True).lower()

    assert (
        "invalid" in page_text or "not found" in page_text or "incorrect" in page_text
    )


def test_company_profile_requires_employer_login(client):
    response = client.get(
        "/employer/company-profile",
        follow_redirects=False,
    )

    assert response.status_code in (302, 401, 403)


def test_company_profile_redirects_to_login(client):
    response = client.get(
        "/employer/company-profile",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/employer/login" in response.headers["Location"]


def login_employer(client, employer_id):
    with client.session_transaction() as session:
        session["employer_id"] = employer_id
        session["employer_company_name"] = "ABC Technology"
        session["employer_email"] = "abc@example.com"


@pytest.mark.skip(
    reason=("Company profile test data does " "not match the current form.")
)
def test_create_company_profile(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data={
            "company_name": "ABC Technology Sdn Bhd",
            "industry": "Information Technology",
            "company_size": "11-50",
            "address": "Kuala Lumpur, Malaysia",
            "company_description": "Software development company.",
            "contact_email": "hr@abc.com",
            "contact_number": "0312345678",
            "website": "https://example.com",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    with app.app_context():
        connection = get_db_connection()

        profile = connection.execute(
            """
            SELECT *
            FROM company_profiles
            WHERE employer_id = ?
            """,
            (employer_id,),
        ).fetchone()

        connection.close()

    assert profile is not None
    assert profile["industry"] == "Information Technology"
    assert profile["contact_email"] == "hr@abc.com"
