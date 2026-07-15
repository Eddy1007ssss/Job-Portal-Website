import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.app import app


def test_health() -> None:
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}