import pytest

from app import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True, "RATE_LIMIT": 1000}).test_client()
