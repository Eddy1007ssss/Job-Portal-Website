from werkzeug.security import check_password_hash, generate_password_hash

from src.admin import get_account_totals, get_registered_users
from src.database import get_db_connection, init_database


def insert_admin(
    app,
    *,
    full_name: str = "System Admin",
    email: str = "admin@example.com",
    role: str = "super_admin",
    is_active: int = 1,
) -> int:
    with app.app_context():
        connection = get_db_connection()
        cursor = connection.execute(
            """
            INSERT INTO admins (
                full_name,
                email,
                password_hash,
                role,
                is_active
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                full_name,
                email,
                generate_password_hash("password123"),
                role,
                is_active,
            ),
        )
        assert cursor.lastrowid is not None
        admin_id = int(cursor.lastrowid)
        connection.commit()
        connection.close()
    return admin_id


def login_admin(client, app) -> None:
    with app.app_context():
        connection = get_db_connection()
        admin = connection.execute("""
            SELECT admin_id, full_name, email, role
            FROM admins
            ORDER BY admin_id
            LIMIT 1
            """).fetchone()
        connection.close()

    if admin is None:
        insert_admin(app)
        with app.app_context():
            connection = get_db_connection()
            admin = connection.execute("""
                SELECT admin_id, full_name, email, role
                FROM admins
                ORDER BY admin_id
                LIMIT 1
                """).fetchone()
            connection.close()

    assert admin is not None
    with client.session_transaction() as admin_session:
        admin_session["admin_id"] = int(admin["admin_id"])
        admin_session["admin_name"] = admin["full_name"]
        admin_session["admin_email"] = admin["email"]
        admin_session["admin_role"] = admin["role"]
        admin_session["admin_authenticated"] = True


def insert_accounts(app, *, seeker_count: int, employer_count: int) -> None:
    with app.app_context():
        connection = get_db_connection()

        for number in range(seeker_count):
            connection.execute(
                """
                INSERT INTO seekers (
                    full_name,
                    email,
                    contact_number,
                    password_hash,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"Seeker {number:02d}",
                    f"seeker{number:02d}@example.com",
                    f"012-100-{number:04d}",
                    "hash",
                    0 if number == 0 else 1,
                ),
            )

        for number in range(employer_count):
            connection.execute(
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
                    f"Company {number:02d}",
                    f"company{number:02d}@example.com",
                    f"03-200-{number:04d}",
                    "hash",
                ),
            )

        connection.commit()
        connection.close()


def insert_deactivated_login_accounts(app) -> None:
    with app.app_context():
        connection = get_db_connection()
        password_hash = generate_password_hash("password123")
        connection.execute(
            """
            INSERT INTO seekers (
                full_name,
                email,
                contact_number,
                password_hash,
                is_active
            )
            VALUES (?, ?, ?, ?, 0)
            """,
            (
                "Blocked Seeker",
                "blocked-seeker@example.com",
                "012-345-6789",
                password_hash,
            ),
        )
        connection.execute(
            """
            INSERT INTO employers (
                company_name,
                company_email,
                contact_number,
                password_hash,
                is_active
            )
            VALUES (?, ?, ?, ?, 0)
            """,
            (
                "Blocked Company",
                "blocked-company@example.com",
                "03-1234-5678",
                password_hash,
            ),
        )
        connection.commit()
        connection.close()


def test_admin_users_requires_admin_login(client):
    response = client.get("/admin/users")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_first_admin_setup_creates_account_and_signs_in(app, client):
    response = client.post(
        "/admin/setup",
        data={
            "full_name": "Platform Admin",
            "email": "ADMIN@example.com",
            "password": "secure123",
            "confirm_password": "secure123",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    with client.session_transaction() as admin_session:
        assert admin_session["admin_authenticated"] is True
        assert admin_session["admin_email"] == "admin@example.com"
        assert admin_session["admin_role"] == "super_admin"

    with app.app_context():
        connection = get_db_connection()
        admin = connection.execute(
            "SELECT full_name, email, role FROM admins"
        ).fetchone()
        connection.close()

    assert admin is not None
    assert admin["full_name"] == "Platform Admin"
    assert admin["email"] == "admin@example.com"
    assert admin["role"] == "super_admin"


def test_admin_setup_validates_form(client):
    response = client.post(
        "/admin/setup",
        data={
            "full_name": "A",
            "email": "not-an-email",
            "password": "short",
            "confirm_password": "different",
        },
    )

    assert response.status_code == 200
    assert b"Full name must contain at least 2 characters." in response.data
    assert b"Please enter a valid email address." in response.data
    assert b"Password must contain at least 8 characters." in response.data
    assert b"Passwords do not match." in response.data


def test_setup_is_disabled_after_first_admin_exists(app, client):
    insert_admin(app)

    response = client.get("/admin/setup")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_admin_can_log_in_and_log_out(app, client):
    insert_admin(app)

    login_response = client.post(
        "/admin/login",
        data={"email": "admin@example.com", "password": "password123"},
    )

    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/admin/users")

    logout_response = client.post("/admin/logout")
    assert logout_response.status_code == 302
    assert logout_response.headers["Location"].endswith("/admin/login")

    protected_response = client.get("/admin/users")
    assert protected_response.status_code == 302


def test_admin_login_rejects_invalid_password(app, client):
    insert_admin(app)

    response = client.post(
        "/admin/login",
        data={"email": "admin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Incorrect email or password." in response.data


def test_user_list_displays_seekers_and_employers(app, client):
    insert_accounts(app, seeker_count=2, employer_count=1)
    login_admin(client, app)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b"Seeker 00" in response.data
    assert b"seeker00@example.com" in response.data
    assert b"Company 00" in response.data
    assert b"company00@example.com" in response.data
    assert b"Deactivated" in response.data


def test_user_list_filters_account_type_and_searches(app, client):
    insert_accounts(app, seeker_count=2, employer_count=2)
    login_admin(client, app)

    employer_response = client.get("/admin/users?type=employer")
    search_response = client.get("/admin/users?search=Seeker+01")

    assert employer_response.status_code == 200
    assert b"Company 00" in employer_response.data
    assert b"Seeker 00" not in employer_response.data

    assert search_response.status_code == 200
    assert b"Seeker 01" in search_response.data
    assert b"Seeker 00" not in search_response.data
    assert b"Company 00" not in search_response.data


def test_user_list_paginates_ten_accounts_per_page(app, client):
    insert_accounts(app, seeker_count=12, employer_count=0)
    login_admin(client, app)

    first_page = client.get("/admin/users?page=1")
    second_page = client.get("/admin/users?page=2")

    assert first_page.status_code == 200
    assert b"Page 1 of 2" in first_page.data
    assert first_page.data.count(b'class="admin-user-avatar seeker"') == 10

    assert second_page.status_code == 200
    assert b"Page 2 of 2" in second_page.data
    assert second_page.data.count(b'class="admin-user-avatar seeker"') == 2


def test_user_query_helpers_return_totals_and_clamp_page(app):
    insert_accounts(app, seeker_count=2, employer_count=3)

    with app.app_context():
        connection = get_db_connection()
        totals = get_account_totals(connection)
        user_page = get_registered_users(
            connection,
            account_type="employer",
            page=99,
            per_page=2,
        )
        connection.close()

    assert totals == {"all": 5, "seekers": 2, "employers": 3, "active": 4}
    assert user_page.total_users == 3
    assert user_page.total_pages == 2
    assert user_page.page == 2
    assert len(user_page.users) == 1


def test_status_update_requires_admin_login(app, client):
    insert_accounts(app, seeker_count=1, employer_count=0)

    response = client.post(
        "/admin/users/seeker/1/status",
        data={"action": "deactivate"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_admin_can_deactivate_and_reactivate_account(app, client):
    insert_accounts(app, seeker_count=1, employer_count=0)
    login_admin(client, app)

    deactivate_response = client.post(
        "/admin/users/seeker/1/status",
        data={
            "action": "deactivate",
            "return_type": "seeker",
            "return_search": "Seeker",
            "return_page": "1",
        },
        follow_redirects=True,
    )

    assert deactivate_response.status_code == 200
    assert b"Seeker 00&#39;s account has been deactivated." in deactivate_response.data
    assert b"Deactivated" in deactivate_response.data
    assert b"Reactivate" in deactivate_response.data

    with app.app_context():
        connection = get_db_connection()
        deactivated = connection.execute(
            "SELECT is_active FROM seekers WHERE seeker_id = 1"
        ).fetchone()
        connection.close()

    assert deactivated is not None
    assert deactivated["is_active"] == 0

    reactivate_response = client.post(
        "/admin/users/seeker/1/status",
        data={"action": "activate"},
        follow_redirects=True,
    )

    assert reactivate_response.status_code == 200
    assert b"Seeker 00&#39;s account has been reactivated." in reactivate_response.data

    with app.app_context():
        connection = get_db_connection()
        reactivated = connection.execute(
            "SELECT is_active FROM seekers WHERE seeker_id = 1"
        ).fetchone()
        connection.close()

    assert reactivated is not None
    assert reactivated["is_active"] == 1


def test_status_update_rejects_invalid_action(app, client):
    insert_accounts(app, seeker_count=0, employer_count=1)
    login_admin(client, app)

    response = client.post(
        "/admin/users/employer/1/status",
        data={"action": "delete"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Select a valid account status action." in response.data

    with app.app_context():
        connection = get_db_connection()
        employer = connection.execute(
            "SELECT is_active FROM employers WHERE employer_id = 1"
        ).fetchone()
        connection.close()

    assert employer is not None
    assert employer["is_active"] == 1


def test_deactivated_seeker_and_employer_cannot_log_in(app, client):
    insert_deactivated_login_accounts(app)

    seeker_response = client.post(
        "/seeker/login",
        data={
            "email": "blocked-seeker@example.com",
            "password": "password123",
        },
    )
    employer_response = client.post(
        "/employer/login",
        data={
            "company_email": "blocked-company@example.com",
            "password": "password123",
        },
    )

    expected_message = (
        b"Your account has been deactivated. Please contact an administrator."
    )
    assert seeker_response.status_code == 200
    assert expected_message in seeker_response.data
    assert employer_response.status_code == 200
    assert expected_message in employer_response.data


def test_existing_session_is_ended_after_account_is_deactivated(app, client):
    insert_accounts(app, seeker_count=1, employer_count=0)
    login_admin(client, app)
    client.post(
        "/admin/users/seeker/1/status",
        data={"action": "deactivate"},
    )

    seeker_client = app.test_client()
    with seeker_client.session_transaction() as seeker_session:
        seeker_session["seeker_id"] = 1
        seeker_session["seeker_name"] = "Seeker 00"
        seeker_session["seeker_email"] = "seeker00@example.com"
        seeker_session["seeker_authenticated"] = True

    response = seeker_client.get("/jobs")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/seeker/login")
    with seeker_client.session_transaction() as seeker_session:
        assert "seeker_id" not in seeker_session


def test_existing_first_admin_is_promoted_to_super_admin(app):
    admin_id = insert_admin(app, role="admin")

    init_database(app)

    with app.app_context():
        connection = get_db_connection()
        administrator = connection.execute(
            "SELECT role FROM admins WHERE admin_id = ?",
            (admin_id,),
        ).fetchone()
        connection.close()

    assert administrator is not None
    assert administrator["role"] == "super_admin"


def test_manage_administrators_requires_login(client):
    response = client.get("/admin/administrators")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_regular_admin_cannot_manage_administrators(app, client):
    insert_admin(app, role="admin")

    login_response = client.post(
        "/admin/login",
        data={"email": "admin@example.com", "password": "password123"},
    )
    manage_response = client.get("/admin/administrators")

    assert login_response.status_code == 302
    assert manage_response.status_code == 403


def test_super_admin_can_view_administrator_accounts(app, client):
    insert_admin(app)
    insert_admin(
        app,
        full_name="Recruitment Admin",
        email="recruitment@example.com",
        role="admin",
    )
    login_admin(client, app)

    response = client.get("/admin/administrators")

    assert response.status_code == 200
    assert b"Manage Administrators" in response.data
    assert b"System Admin" in response.data
    assert b"Recruitment Admin" in response.data
    assert b"Super Admin" in response.data


def test_super_admin_can_create_another_administrator(app, client):
    insert_admin(app)
    login_admin(client, app)

    response = client.post(
        "/admin/administrators/add",
        data={
            "full_name": "Content Admin",
            "email": "content@example.com",
            "role": "admin",
            "password": "newpassword123",
            "confirm_password": "newpassword123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Administrator account for Content Admin was created." in response.data
    assert b"content@example.com" in response.data

    with app.app_context():
        connection = get_db_connection()
        created_admin = connection.execute("""
            SELECT role, is_active, password_hash
            FROM admins
            WHERE email = 'content@example.com'
            """).fetchone()
        connection.close()

    assert created_admin is not None
    assert created_admin["role"] == "admin"
    assert created_admin["is_active"] == 1
    assert check_password_hash(created_admin["password_hash"], "newpassword123")

    new_admin_client = app.test_client()
    login_response = new_admin_client.post(
        "/admin/login",
        data={"email": "content@example.com", "password": "newpassword123"},
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/admin/users")
    assert new_admin_client.get("/admin/administrators").status_code == 403


def test_add_administrator_validates_fields_and_duplicate_email(app, client):
    insert_admin(app)
    login_admin(client, app)

    invalid_response = client.post(
        "/admin/administrators/add",
        data={
            "full_name": "A",
            "email": "invalid-email",
            "role": "owner",
            "password": "short",
            "confirm_password": "different",
        },
        follow_redirects=True,
    )

    assert invalid_response.status_code == 200
    assert (
        b"Administrator name must contain at least 2 characters."
        in invalid_response.data
    )
    assert b"Please enter a valid administrator email address." in invalid_response.data
    assert (
        b"Administrator password must contain at least 8 characters."
        in invalid_response.data
    )
    assert b"Administrator passwords do not match." in invalid_response.data
    assert b"Select a valid administrator role." in invalid_response.data

    duplicate_response = client.post(
        "/admin/administrators/add",
        data={
            "full_name": "Duplicate Admin",
            "email": "admin@example.com",
            "role": "admin",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )

    assert duplicate_response.status_code == 200
    assert (
        b"An administrator with this email already exists." in duplicate_response.data
    )


def test_super_admin_can_deactivate_and_reactivate_another_admin(app, client):
    insert_admin(app)
    second_admin_id = insert_admin(
        app,
        full_name="Support Admin",
        email="support@example.com",
        role="admin",
    )
    login_admin(client, app)

    second_admin_client = app.test_client()
    second_admin_client.post(
        "/admin/login",
        data={"email": "support@example.com", "password": "password123"},
    )

    deactivate_response = client.post(
        f"/admin/administrators/{second_admin_id}/status",
        data={"action": "deactivate"},
        follow_redirects=True,
    )

    assert deactivate_response.status_code == 200
    assert b"administrator account was deactivated." in deactivate_response.data
    assert second_admin_client.get("/admin/users").status_code == 302

    blocked_login = app.test_client().post(
        "/admin/login",
        data={"email": "support@example.com", "password": "password123"},
    )
    assert blocked_login.status_code == 200
    assert b"Your administrator account has been deactivated." in blocked_login.data

    reactivate_response = client.post(
        f"/admin/administrators/{second_admin_id}/status",
        data={"action": "activate"},
        follow_redirects=True,
    )
    assert reactivate_response.status_code == 200
    assert b"administrator account was reactivated." in reactivate_response.data

    restored_login = app.test_client().post(
        "/admin/login",
        data={"email": "support@example.com", "password": "password123"},
    )
    assert restored_login.status_code == 302
    assert restored_login.headers["Location"].endswith("/admin/users")


def test_super_admin_cannot_deactivate_own_account(app, client):
    admin_id = insert_admin(app)
    login_admin(client, app)

    response = client.post(
        f"/admin/administrators/{admin_id}/status",
        data={"action": "deactivate"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You cannot deactivate your own administrator account." in response.data

    with app.app_context():
        connection = get_db_connection()
        administrator = connection.execute(
            "SELECT is_active FROM admins WHERE admin_id = ?",
            (admin_id,),
        ).fetchone()
        connection.close()

    assert administrator is not None
    assert administrator["is_active"] == 1
