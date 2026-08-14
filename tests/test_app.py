def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200


def test_dashboard_page(client):
    response = client.get("/dashboard")

    assert response.status_code == 200


def test_companies_page(client):
    response = client.get("/companies")

    assert response.status_code == 200


def test_about_page(client):
    response = client.get("/about")

    assert response.status_code == 200
    assert b"About Us" in response.data


def test_unknown_page_returns_404(client):
    response = client.get("/this-page-does-not-exist")

    assert response.status_code == 404


def test_saved_jobs_page_requires_login(client):
    response = client.get("/saved-jobs")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/seeker/login")


def test_job_alerts_page_requires_login(client):
    response = client.get("/job-alerts")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/seeker/login")


def test_settings_page_requires_login(client):
    response = client.get("/settings")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/seeker/login")
