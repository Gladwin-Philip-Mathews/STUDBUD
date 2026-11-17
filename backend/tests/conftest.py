import pytest

from app.db import connect, init_db


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


from datetime import datetime, timedelta, timezone

from app import create_app


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def app(tmp_path, clock):
    app = create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "t.db"), "CLOCK": clock,
                      "SECRET_KEY": "test", "BASE_URL": "http://app",
                      "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000", "EMAIL_DISPATCH": "manual"})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def gateway(app):
    return app.extensions["email_gateway"]
