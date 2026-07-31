from werkzeug.security import check_password_hash, generate_password_hash

from src.database import get_db_connection


def valid_registration_data(**changes):
    data = {
        "full_name": "Alicia Tan",
        "email": "alicia@example.com",
        "contact_number": "0123456789",
        "password": "Password123",
        "confirm_password": "Password123",
    }

    data.update(changes)
    return data


def create_seeker(app, email="existing@example.com"):
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
                "Existing Seeker",
                email,
                "0123456789",
                generate_password_hash("Password123"),
            ),
        )
        seeker_id = int(cursor.lastrowid)
        connection.execute(
            "INSERT INTO seeker_profiles (seeker_id) VALUES (?)",
            (seeker_id,),
        )
        connection.commit()
        connection.close()

    return seeker_id


def test_seeker_register_page_loads(client):
    response = client.get("/seeker/register")

    assert response.status_code == 200
    assert "Create Your Account" in response.get_data(as_text=True)
    assert "Phone Number" in response.get_data(as_text=True)


def test_register_seeker_successfully(client, app):
    response = client.post(
        "/seeker/register",
        data=valid_registration_data(),
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/jobs")

    with app.app_context():
        connection = get_db_connection()
        seeker = connection.execute(
            "SELECT * FROM seekers WHERE email = ?",
            ("alicia@example.com",),
        ).fetchone()
        profile = connection.execute(
            "SELECT * FROM seeker_profiles WHERE seeker_id = ?",
            (seeker["seeker_id"],),
        ).fetchone()
        connection.close()

    assert seeker is not None
    assert seeker["full_name"] == "Alicia Tan"
    assert seeker["contact_number"] == "0123456789"
    assert seeker["password_hash"] != "Password123"
    assert check_password_hash(seeker["password_hash"], "Password123")
    assert profile is not None

    with client.session_transaction() as current_session:
        assert current_session["seeker_id"] == seeker["seeker_id"]
        assert current_session["seeker_name"] == "Alicia Tan"


def test_register_seeker_with_short_name(client):
    response = client.post(
        "/seeker/register",
        data=valid_registration_data(full_name="A"),
    )

    assert response.status_code == 200
    assert "Full name must contain at least 2 characters" in response.get_data(
        as_text=True
    )


def test_register_seeker_with_invalid_email(client):
    response = client.post(
        "/seeker/register",
        data=valid_registration_data(email="invalid-email"),
    )

    assert response.status_code == 200
    assert "Please enter a valid email address" in response.get_data(as_text=True)


def test_register_seeker_with_invalid_phone_number(client):
    response = client.post(
        "/seeker/register",
        data=valid_registration_data(contact_number="123ABC"),
    )

    assert response.status_code == 200
    assert "Phone number must contain between 8 and 15" in response.get_data(
        as_text=True
    )


def test_register_seeker_with_short_password(client):
    response = client.post(
        "/seeker/register",
        data=valid_registration_data(
            password="short",
            confirm_password="short",
        ),
    )

    assert response.status_code == 200
    assert "Password must contain at least 8 characters" in response.get_data(
        as_text=True
    )


def test_register_seeker_with_password_mismatch(client):
    response = client.post(
        "/seeker/register",
        data=valid_registration_data(confirm_password="Different123"),
    )

    assert response.status_code == 200
    assert "Passwords do not match" in response.get_data(as_text=True)


def test_register_seeker_with_duplicate_email(client, app):
    create_seeker(app)

    response = client.post(
        "/seeker/register",
        data=valid_registration_data(email="existing@example.com"),
    )

    assert response.status_code == 200
    assert "This email address is already registered" in response.get_data(as_text=True)


def test_logged_in_seeker_is_redirected_from_registration(client, app):
    seeker_id = create_seeker(app)

    with client.session_transaction() as current_session:
        current_session["seeker_id"] = seeker_id

    response = client.get("/seeker/register", follow_redirects=False)

    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/jobs")
