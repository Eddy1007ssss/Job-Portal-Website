import os

import pytest

from src.app import app as flask_app
from src.database import init_database


@pytest.fixture()
def app(tmp_path):
    test_database_path = tmp_path / "test_jobportal.db"

    previous_database_path = os.environ.get("DATABASE_PATH")

    # Remember Flask's real static folder.
    original_static_folder = flask_app.static_folder

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="pytest-secret-key",
        DATABASE_PATH=str(test_database_path),
    )

    init_database(flask_app)

    yield flask_app

    # Restore the static folder after every test.
    flask_app.static_folder = original_static_folder

    if previous_database_path is None:
        os.environ.pop(
            "DATABASE_PATH",
            None,
        )
    else:
        os.environ["DATABASE_PATH"] = previous_database_path


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()