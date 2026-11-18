import re

GOOD = {"email": "ana@g.rit.edu", "displayName": "Ana Lee", "password": "passw0rdX", "acceptNotice": True}


def token_from(gateway, index=-1):
    return re.search(r"token=([\w-]+)", gateway.sent[index].body).group(1)


def register(client, **over):
    return client.post("/api/auth/register", json={**GOOD, **over})


def verified_account(client, gateway):
    register(client)
    client.post("/api/auth/verify", json={"token": token_from(gateway)})


def sign_in(client, password="passw0rdX", email="ana@g.rit.edu"):
    return client.post("/api/auth/sign-in", json={"email": email, "password": password})


def test_register_creates_unverified_account_and_sends_one_message(client, gateway):  # AC-FR-001a
    assert register(client).status_code == 202
    assert len(gateway.sent) == 1 and gateway.sent[0].to == "ana@g.rit.edu"


def test_unverified_account_cannot_sign_in(client, gateway):  # AC-FR-001b, AC-FR-007a
    register(client)
    r = sign_in(client)
    assert r.status_code == 403 and r.get_json()["canResend"] is True
    assert client.get("/api/auth/me").status_code == 401


def test_non_rit_domains_rejected_no_account_no_message(client, gateway):  # AC-FR-002b
    for email in ("x@other.com", "x@g.rit.edu.other.com"):
        r = register(client, email=email)
        assert r.status_code == 400 and "RIT" in r.get_json()["errors"]["email"]
    assert gateway.sent == []
    assert register(client, email="x@G.RIT.EDU").status_code == 202  # letter case ignored


def test_password_rules_name_the_field(client):  # AC-FR-003a
    for pw in ("short1", "lettersonly"):
        assert "password" in register(client, password=pw).get_json()["errors"]


def test_display_name_rules(client):  # AC-FR-003b
    assert "displayName" in register(client, displayName="ab").get_json()["errors"]
    assert "displayName" in register(client, displayName="x" * 31).get_json()["errors"]
    register(client)
    assert "displayName" in register(client, email="b@g.rit.edu").get_json()["errors"]


def test_duplicate_email_gives_same_message_and_no_second_account(client, gateway):  # AC-FR-004a
    first = register(client)
    second = register(client)
    assert first.get_json() == second.get_json()
    assert len(gateway.sent) == 1


def test_verify_within_24_hours_then_link_is_single_use(client, gateway, clock):  # AC-FR-005a
    register(client)
    clock.advance(hours=23)
    tok = token_from(gateway)
    assert client.post("/api/auth/verify", json={"token": tok}).status_code == 200
    assert client.post("/api/auth/verify", json={"token": tok}).status_code == 400
    assert sign_in(client).status_code == 200


def test_expired_link_leaves_account_unverified(client, gateway, clock):  # AC-FR-005b, AC-FR-006a
    register(client)
    clock.advance(hours=24, minutes=1)
    r = client.post("/api/auth/verify", json={"token": token_from(gateway)})
    assert r.status_code == 400 and r.get_json()["canResend"] is True
    assert sign_in(client).status_code == 403


def test_malformed_link_is_rejected(client):
    assert client.post("/api/auth/verify", json={"token": "nonsense"}).status_code == 400
    assert client.post("/api/auth/verify", json={}).status_code == 400


def test_resend_limit_three_per_hour_and_old_links_stop_working(client, gateway):  # AC-FR-006b
    register(client)
    first = token_from(gateway)
    for _ in range(3):
        assert client.post("/api/auth/resend", json={"email": GOOD["email"]}).status_code == 202
    sent_before = len(gateway.sent)
    assert client.post("/api/auth/resend", json={"email": GOOD["email"]}).status_code == 429
    assert len(gateway.sent) == sent_before
    assert client.post("/api/auth/verify", json={"token": first}).status_code == 400
    assert client.post("/api/auth/verify", json={"token": token_from(gateway)}).status_code == 200


def test_sign_in_success_and_me(client, gateway):  # AC-FR-008a
    verified_account(client, gateway)
    r = sign_in(client)
    assert r.status_code == 200 and "password" not in str(r.get_json()).lower()
    assert client.get("/api/auth/me").get_json()["account"]["displayName"] == "Ana Lee"


def test_wrong_password_and_unknown_email_same_message(client, gateway):  # AC-FR-008b
    verified_account(client, gateway)
    a = sign_in(client, password="wrongpass1")
    b = sign_in(client, email="nobody@g.rit.edu")
    assert a.status_code == b.status_code == 401 and a.get_json() == b.get_json()


def test_lockout_after_five_failures_then_released(client, gateway, clock):  # AC-FR-009a
    verified_account(client, gateway)
    for _ in range(5):
        sign_in(client, password="bad")
        clock.advance(minutes=1)
    clock.advance(minutes=4)  # minute 5 after the last failure
    assert sign_in(client).status_code == 429
    clock.advance(minutes=11)  # minute 16
    assert sign_in(client).status_code == 200


def test_idle_session_ends_after_two_hours(client, gateway, clock):  # NFR-011
    verified_account(client, gateway); sign_in(client)
    clock.advance(hours=1, minutes=59)
    assert client.get("/api/auth/me").status_code == 200
    clock.advance(hours=2, minutes=1)
    assert client.get("/api/auth/me").status_code == 401


def test_sign_out_ends_session(client, gateway):
    verified_account(client, gateway); sign_in(client)
    client.post("/api/auth/sign-out")
    assert client.get("/api/auth/me").status_code == 401


def test_suspended_account_loses_access_at_next_request(client, gateway, app):  # FR-066
    verified_account(client, gateway); sign_in(client)
    import sqlite3
    c = sqlite3.connect(app.config["DATABASE_PATH"])
    c.execute("UPDATE accounts SET status = 'suspended'"); c.commit(); c.close()
    assert client.get("/api/auth/me").status_code == 401
    assert sign_in(client).status_code == 403


def test_no_password_or_token_stored_in_clear(client, gateway, app):  # NFR-009
    register(client)
    import sqlite3
    c = sqlite3.connect(app.config["DATABASE_PATH"])
    pw = c.execute("SELECT password_hash FROM accounts").fetchone()[0]
    th = c.execute("SELECT token_hash FROM verification_tokens").fetchone()[0]
    c.close()
    assert "passw0rdX" not in pw and token_from(gateway) != th


def test_registration_needs_the_notice_accepted_and_records_when(client, gateway, app):  # OR-003
    r = register(client, acceptNotice=False)
    assert r.status_code == 400 and "acceptNotice" in r.get_json()["errors"]
    assert gateway.sent == []
    assert register(client).status_code == 202
    from app.db import connect
    row = connect(app.config["DATABASE_PATH"]).execute("SELECT notice_accepted_at FROM accounts").fetchone()
    assert row["notice_accepted_at"]
