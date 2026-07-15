import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.app import health


def test_health():
    assert health() == {"status": "ok"}