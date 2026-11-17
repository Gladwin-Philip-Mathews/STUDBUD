"""Test helpers shared by feature tests: create verified students and sign them in."""
from werkzeug.security import generate_password_hash

from app.db import connect
from app.models import Account, AccountStatus, Profile
from app.repositories import SqliteAccountRepository, SqliteProfileRepository

PASSWORD = "passw0rdX"


def make_student(app, name, email=None, status=AccountStatus.VERIFIED, profile=None):
    """Create an account (and optional Profile) directly in the database. Returns the account id."""
    conn = connect(app.config["DATABASE_PATH"])
    try:
        acct = SqliteAccountRepository(conn).add(Account(
            email or f"{name.lower()}@g.rit.edu", name,
            generate_password_hash(PASSWORD, method="pbkdf2:sha256:1000"), status=status))
        if profile is not None:
            profile.account_id = acct.id
            SqliteProfileRepository(conn).save(profile)
        return acct.id
    finally:
        conn.close()


def signed_in_client(app, name):
    client = app.test_client()
    r = client.post("/api/auth/sign-in", json={"email": f"{name.lower()}@g.rit.edu", "password": PASSWORD})
    assert r.status_code == 200, r.get_json()
    return client
