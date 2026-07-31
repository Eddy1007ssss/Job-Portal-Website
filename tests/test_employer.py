import io

from PIL import Image
from werkzeug.security import generate_password_hash

from src.database import get_db_connection

# =========================================================
# Reusable test data
# =========================================================


def valid_registration_data(**changes):
    data = {
        "company_name": "ABC Technology Sdn Bhd",
        "company_email": "abc@example.com",
        "contact_number": "0123456789",
        "password": "Password123",
        "confirm_password": "Password123",
    }

    data.update(changes)
    return data


def valid_company_profile_data(**changes):
    data = {
        "company_name": "ABC Technology Sdn Bhd",
        "industry": "Information Technology",
        "company_size": "11-50 employees",
        "address": "Kuala Lumpur, Malaysia",
        "company_description": (
            "ABC Technology provides professional software development "
            "and technology consulting services."
        ),
        "contact_email": "hr@abc.com",
        "contact_number": "0312345678",
        "website": "https://example.com",
    }

    data.update(changes)
    return data


# =========================================================
# Database and session helpers
# =========================================================


def create_employer(
    app,
    company_name="ABC Technology",
    company_email="abc@example.com",
    contact_number="0123456789",
    password="Password123",
):
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
                company_email,
                contact_number,
                generate_password_hash(password),
            ),
        )

        employer_id = int(cursor.lastrowid)

        connection.commit()
        connection.close()

    return employer_id


def login_employer(
    client,
    employer_id,
    company_name="ABC Technology",
    company_email="abc@example.com",
):
    with client.session_transaction() as session:
        session["employer_id"] = employer_id
        session["employer_company_name"] = company_name
        session["employer_email"] = company_email


def get_company_profile(app, employer_id):
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

    return profile


def create_test_image(
    filename="logo.jpg",
    image_format="JPEG",
    size=(100, 100),
):
    image_stream = io.BytesIO()

    image = Image.new(
        "RGB",
        size,
        (255, 255, 255),
    )

    image.save(
        image_stream,
        format=image_format,
    )

    image_stream.seek(0)

    return image_stream, filename


# =========================================================
# Employer page tests
# =========================================================


def test_employer_register_page_loads(client):
    response = client.get("/employer/register")

    assert response.status_code == 200


def test_employer_login_page_loads(client):
    response = client.get("/employer/login")

    assert response.status_code == 200


# =========================================================
# Employer registration tests
# =========================================================


def test_register_employer_successfully(client, app):
    response = client.post(
        "/employer/register",
        data=valid_registration_data(),
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


def test_register_company_name_too_short(client):
    response = client.post(
        "/employer/register",
        data=valid_registration_data(company_name="A"),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company name must contain at least 2 characters" in response.get_data(
        as_text=True
    )


def test_register_invalid_email(client):
    response = client.post(
        "/employer/register",
        data=valid_registration_data(
            company_email="invalid-email",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Please enter a valid company email" in response.get_data(as_text=True)


def test_register_contact_number_too_short(client):
    response = client.post(
        "/employer/register",
        data=valid_registration_data(
            contact_number="123",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Contact number must contain between" in response.get_data(as_text=True)


def test_register_contact_number_invalid_characters(client):
    response = client.post(
        "/employer/register",
        data=valid_registration_data(
            contact_number="012ABC6789",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Contact number must contain between" in response.get_data(as_text=True)


def test_register_password_too_short(client):
    response = client.post(
        "/employer/register",
        data=valid_registration_data(
            password="1234567",
            confirm_password="1234567",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Password must contain at least 8 characters" in response.get_data(
        as_text=True
    )


def test_register_password_mismatch(client):
    response = client.post(
        "/employer/register",
        data=valid_registration_data(
            confirm_password="DifferentPassword",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Passwords do not match" in response.get_data(as_text=True)


def test_register_duplicate_employer_email(client, app):
    create_employer(
        app,
        company_email="duplicate@example.com",
    )

    response = client.post(
        "/employer/register",
        data=valid_registration_data(
            company_email="duplicate@example.com",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "This company email is already registered" in response.get_data(as_text=True)


# =========================================================
# Employer login and logout tests
# =========================================================


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
    assert "Incorrect email or password" in response.get_data(as_text=True)


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
    assert "Incorrect email or password" in response.get_data(as_text=True)


def test_employer_logout_clears_session(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.get(
        "/employer/logout",
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    with client.session_transaction() as session:
        assert session.get("employer_id") is None
        assert session.get("employer_email") is None


# =========================================================
# Company profile access tests
# =========================================================


def test_company_profile_requires_employer_login(client):
    response = client.get(
        "/employer/company-profile",
        follow_redirects=False,
    )

    assert response.status_code == 302


def test_company_profile_redirects_to_login(client):
    response = client.get(
        "/employer/company-profile",
        follow_redirects=False,
    )

    assert "/employer/login" in response.headers["Location"]


def test_company_profile_page_loads_for_logged_in_employer(
    client,
    app,
):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.get("/employer/company-profile")

    assert response.status_code == 200


# =========================================================
# Company profile validation tests
# =========================================================


def test_company_profile_company_name_too_short(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            company_name="A",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company name must contain at least 2 characters" in response.get_data(
        as_text=True
    )


def test_company_profile_industry_required(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            industry="",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Please select an industry" in response.get_data(as_text=True)


def test_company_profile_address_too_short(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            address="KL",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Please enter the complete company address" in response.get_data(
        as_text=True
    )


def test_company_profile_description_too_short(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            company_description="Too short",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert (
        "Company description must contain at least 30 characters"
        in response.get_data(as_text=True)
    )


def test_company_profile_description_too_long(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            company_description="A" * 1501,
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company description cannot exceed 1500 characters" in response.get_data(
        as_text=True
    )


def test_company_profile_invalid_contact_email(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            contact_email="invalid-email",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Please enter a valid contact email" in response.get_data(as_text=True)


def test_company_profile_invalid_contact_number(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            contact_number="123",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Contact number must contain between" in response.get_data(as_text=True)


# =========================================================
# Company profile create, update and preview tests
# =========================================================


def test_create_company_profile(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(),
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    profile = get_company_profile(app, employer_id)

    assert profile is not None
    assert profile["industry"] == "Information Technology"
    assert profile["contact_email"] == "hr@abc.com"
    assert profile["company_size"] == "11-50 employees"


def test_update_existing_company_profile(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    first_response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(),
        follow_redirects=False,
    )

    assert first_response.status_code in (302, 303)

    second_response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            company_name="ABC Technology Updated",
            industry="Finance",
        ),
        follow_redirects=False,
    )

    assert second_response.status_code in (302, 303)

    profile = get_company_profile(app, employer_id)

    assert profile["company_name"] == "ABC Technology Updated"
    assert profile["industry"] == "Finance"


def test_company_preview_requires_existing_profile(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    response = client.get(
        "/employer/company-profile/preview",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/employer/company-profile" in response.headers["Location"]


def test_company_preview_loads_after_profile_creation(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(),
        follow_redirects=False,
    )

    response = client.get("/employer/company-profile/preview")

    assert response.status_code == 200


# =========================================================
# Company image upload tests
# =========================================================


def test_upload_valid_jpg_logo(client, app, tmp_path):
    app.static_folder = str(tmp_path / "static")

    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_logo"] = create_test_image(
        filename="logo.jpg",
        image_format="JPEG",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    profile = get_company_profile(app, employer_id)

    assert profile["logo_url"]
    assert profile["logo_url"].endswith(".jpg")


def test_upload_valid_png_logo(client, app, tmp_path):
    app.static_folder = str(tmp_path / "static")

    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_logo"] = create_test_image(
        filename="logo.png",
        image_format="PNG",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    profile = get_company_profile(app, employer_id)

    assert profile["logo_url"]
    assert profile["logo_url"].endswith(".png")


def test_upload_valid_banner(client, app, tmp_path):
    app.static_folder = str(tmp_path / "static")

    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_banner"] = create_test_image(
        filename="banner.jpg",
        image_format="JPEG",
        size=(300, 100),
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    profile = get_company_profile(app, employer_id)

    assert profile["banner_url"]
    assert profile["banner_url"].endswith(".jpg")


def test_upload_logo_with_chinese_filename(client, app, tmp_path):
    app.static_folder = str(tmp_path / "static")

    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_logo"] = create_test_image(
        filename="头像.jpg",
        image_format="JPEG",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    profile = get_company_profile(app, employer_id)

    assert profile["logo_url"]
    assert profile["logo_url"].endswith(".jpg")


def test_upload_invalid_logo_extension(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_logo"] = (
        io.BytesIO(b"not an image"),
        "company.pdf",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company logo must be a PNG or JPG image" in response.get_data(as_text=True)


def test_upload_fake_jpg_logo(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_logo"] = (
        io.BytesIO(b"This is not a real image"),
        "fake.jpg",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company logo is not a valid image" in response.get_data(as_text=True)


def test_upload_empty_logo(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_logo"] = (
        io.BytesIO(b""),
        "empty.jpg",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company logo file is empty" in response.get_data(as_text=True)


def test_upload_logo_larger_than_2mb(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_logo"] = (
        io.BytesIO(b"A" * ((2 * 1024 * 1024) + 1)),
        "large-logo.jpg",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company logo must not exceed 2 MB" in response.get_data(as_text=True)


def test_upload_banner_larger_than_5mb(client, app):
    employer_id = create_employer(app)
    login_employer(client, employer_id)

    data = valid_company_profile_data()
    data["company_banner"] = (
        io.BytesIO(b"A" * ((5 * 1024 * 1024) + 1)),
        "large-banner.jpg",
    )

    response = client.post(
        "/employer/company-profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Company banner must not exceed 5 MB" in response.get_data(as_text=True)


def test_update_profile_without_new_images_preserves_existing_images(
    client,
    app,
    tmp_path,
):
    app.static_folder = str(tmp_path / "static")

    employer_id = create_employer(app)
    login_employer(client, employer_id)

    first_data = valid_company_profile_data()
    first_data["company_logo"] = create_test_image(
        filename="logo.jpg",
        image_format="JPEG",
    )
    first_data["company_banner"] = create_test_image(
        filename="banner.jpg",
        image_format="JPEG",
        size=(300, 100),
    )

    first_response = client.post(
        "/employer/company-profile",
        data=first_data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert first_response.status_code in (302, 303)

    original_profile = get_company_profile(app, employer_id)
    original_logo_url = original_profile["logo_url"]
    original_banner_url = original_profile["banner_url"]

    second_response = client.post(
        "/employer/company-profile",
        data=valid_company_profile_data(
            company_description=(
                "ABC Technology provides updated professional software "
                "development and technology consulting services."
            ),
        ),
        follow_redirects=False,
    )

    assert second_response.status_code in (302, 303)

    updated_profile = get_company_profile(app, employer_id)

    assert updated_profile["logo_url"] == original_logo_url
    assert updated_profile["banner_url"] == original_banner_url
