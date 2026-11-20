"""Checks added by the implementation review against the M2 SRS (20 November 2026).

Each test is named after the planned check it implements: IF-006, NFR-008, NFR-010, DR-007, DR-009, DR-011,
OR-001 and OR-002. See docs/REVIEW.md for the finding behind each one.
"""
import sqlite3
import ssl

import pytest
from click.testing import CliRunner

from app import create_app
from app.container import get_service
from app.db import connect
from app.email_gateway.gateway import tls_context
from app.models import Course
from app.repositories import SqliteCourseRepository

from .helpers import make_student, signed_in_client

PROFILE = {"intent": "both", "cohort": "first year", "interests": [], "courses": ["SWEN-261"]}


def sql(app, query, *args):
    conn = connect(app.config["DATABASE_PATH"])
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


def one(app, query, *args):
    conn = connect(app.config["DATABASE_PATH"])
    try:
        return conn.execute(query, args).fetchone()[0]
    finally:
        conn.close()


@pytest.fixture
def world(app):
    """Ann and Bo share a course community and are connected; Mo moderates; Root administers."""
    conn = connect(app.config["DATABASE_PATH"])
    SqliteCourseRepository(conn).add(Course("SWEN-261", "Intro to Software Engineering"))
    conn.close()
    ids = {n: make_student(app, n) for n in ("Ann", "Bo", "Mo", "Root")}
    sql(app, "UPDATE accounts SET role='moderator' WHERE id=?", ids["Mo"])
    sql(app, "UPDATE accounts SET role='administrator' WHERE id=?", ids["Root"])
    cl = {n: signed_in_client(app, n) for n in ids}
    for n in ("Ann", "Bo"):
        cl[n].put("/api/profile", json=PROFILE)
    community = next(c for c in cl["Ann"].get("/api/communities").get_json()["communities"] if c["kind"] == "course")["id"]
    return {"ids": ids, "c": cl, "community": community}


# ---------------------------------------------------------------- IF-006, NFR-010: secure transport ----

def test_plain_http_is_redirected_and_returns_no_content_when_https_is_enforced(tmp_path, clock):  # TC-IF-006a
    app = create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "s.db"), "CLOCK": clock,
                      "SECRET_KEY": "a-long-random-value-for-the-test", "FORCE_HTTPS": True})
    client = app.test_client()
    r = client.get("/api/health", base_url="http://studbud.example")
    assert r.status_code == 308
    assert r.headers["Location"].startswith("https://studbud.example/api/health")
    assert b"ok" not in r.data  # no page content over HTTP
    assert client.post("/api/auth/sign-in", base_url="http://studbud.example", json={}).status_code == 403
    secure = client.get("/api/health", base_url="https://studbud.example")
    assert secure.status_code == 200
    assert secure.headers["Strict-Transport-Security"].startswith("max-age=")
    behind_proxy = client.get("/api/health", base_url="http://studbud.example",
                              headers={"X-Forwarded-Proto": "https"})
    assert behind_proxy.status_code == 200  # the pilot server terminates TLS in front of Flask
    assert app.config["SESSION_COOKIE_SECURE"] is True and app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_https_mode_refuses_a_placeholder_secret_key(tmp_path, clock):  # NFR-009, IF-006
    with pytest.raises(RuntimeError):
        create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "s.db"), "CLOCK": clock,
                    "SECRET_KEY": "dev", "FORCE_HTTPS": True})


def test_laptop_setup_still_answers_over_plain_http(client):  # FORCE_HTTPS is off by default
    assert client.get("/api/health").status_code == 200
    assert client.application.config["SESSION_COOKIE_HTTPONLY"] is True


def test_email_route_requires_tls_1_2_or_later():  # TC-NFR-010a (server to email service leg)
    context = tls_context()
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert context.verify_mode == ssl.CERT_REQUIRED


# ---------------------------------------------------------------- NFR-008: error handling ----

def test_a_repeated_post_submission_creates_one_post(world):  # TC-NFR-008a (repeat half)
    ann, community = world["c"]["Ann"], world["community"]
    body = {"kind": "question", "title": "Anyone free to study Thursday?", "text": "Library, 4 pm."}
    first = ann.post(f"/api/communities/{community}/posts", json=body)
    again = ann.post(f"/api/communities/{community}/posts", json=body)
    assert first.status_code == 201 and again.status_code == 200
    assert again.get_json()["post"]["id"] == first.get_json()["post"]["id"]
    assert "already published" in again.get_json()["message"]
    assert one(world["c"]["Ann"].application, "SELECT COUNT(*) FROM posts") == 1


def test_a_different_post_is_not_mistaken_for_a_repeat(world, clock):  # NFR-008 boundary
    ann, community = world["c"]["Ann"], world["community"]
    body = {"kind": "question", "title": "Anyone free to study Thursday?", "text": "Library, 4 pm."}
    assert ann.post(f"/api/communities/{community}/posts", json=body).status_code == 201
    assert ann.post(f"/api/communities/{community}/posts", json={**body, "text": "Library, 5 pm."}).status_code == 201
    clock.advance(minutes=6)
    assert ann.post(f"/api/communities/{community}/posts", json=body).status_code == 201  # outside the window
    assert one(ann.application, "SELECT COUNT(*) FROM posts") == 3


def test_failures_show_a_plain_message_without_technical_details(tmp_path, clock, monkeypatch):  # TC-NFR-008a
    app = create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "e.db"), "CLOCK": clock,
                      "SECRET_KEY": "test", "PLAIN_ERRORS": True})
    client = app.test_client()
    missing = client.get("/api/no-such-page")
    assert missing.status_code == 404 and missing.is_json
    assert "not found" in missing.get_json()["message"].lower()
    wrong_method = client.delete("/api/health")
    assert wrong_method.status_code == 405 and wrong_method.is_json

    def broken(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")  # the stopped database of AC-NFR-008a

    import app.controllers.health as health
    monkeypatch.setattr(health, "health", broken)
    app.view_functions["health.health"] = broken
    failed = client.get("/api/health")
    assert failed.status_code == 500 and failed.is_json
    message = failed.get_json()["message"]
    assert "Try again" in message
    for leak in ("sqlite", "OperationalError", "Traceback", "locked"):
        assert leak not in message


# ---------------------------------------------------------------- DR-007, DR-009, DR-011: integrity rules ----

def test_two_open_connections_for_one_pair_cannot_be_stored(conn):  # TC-DR-007a
    now = "2026-11-20T10:00:00+00:00"
    for i, name in enumerate(("a", "b"), start=1):
        conn.execute("INSERT INTO accounts(email, display_name, password_hash, status, created_at) VALUES (?,?,?,?,?)",
                     (f"{name}@g.rit.edu", name, "x", "verified", now))
    conn.execute("INSERT INTO connections(requester_id, receiver_id, status, created_at, status_changed_at) "
                 "VALUES (1, 2, 'pending', ?, ?)", (now, now))
    with pytest.raises(sqlite3.IntegrityError):  # same pair, other direction
        conn.execute("INSERT INTO connections(requester_id, receiver_id, status, created_at, status_changed_at) "
                     "VALUES (2, 1, 'pending', ?, ?)", (now, now))
    conn.execute("UPDATE connections SET status='declined' WHERE id=1")
    conn.execute("INSERT INTO connections(requester_id, receiver_id, status, created_at, status_changed_at) "
                 "VALUES (2, 1, 'pending', ?, ?)", (now, now))  # allowed once the first is no longer open


def test_a_report_reason_outside_the_list_cannot_be_stored(conn):  # TC-DR-009a
    now = "2026-11-20T10:00:00+00:00"
    for name in ("a", "b"):
        conn.execute("INSERT INTO accounts(email, display_name, password_hash, status, created_at) VALUES (?,?,?,?,?)",
                     (f"{name}@g.rit.edu", name, "x", "verified", now))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO safety_reports(reporter_id, reported_student_id, item_type, item_id, reason, "
                     "received_at) VALUES (1, 2, 'student', 2, 'did not like it', ?)", (now,))
    conn.execute("INSERT INTO safety_reports(reporter_id, reported_student_id, item_type, item_id, reason, received_at) "
                 "VALUES (1, 2, 'student', 2, 'spam', ?)", (now,))


def test_a_notification_with_an_unknown_event_type_cannot_be_stored(conn):  # TC-DR-011a
    now = "2026-11-20T10:00:00+00:00"
    conn.execute("INSERT INTO accounts(email, display_name, password_hash, status, created_at) VALUES (?,?,?,?,?)",
                 ("a@g.rit.edu", "a", "x", "verified", now))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO notifications(recipient_id, event_type, body, created_at) VALUES (1, 'PROMOTION', 'x', ?)",
                     (now,))
    conn.execute("INSERT INTO notifications(recipient_id, event_type, body, created_at) VALUES (1, 'REPLY_ADDED', 'x', ?)",
                 (now,))


# ---------------------------------------------------------------- OR-001, OR-002: the clean-up run ----

def _close_a_report(w, text="a rude post"):
    ann, bo, mo = w["c"]["Ann"], w["c"]["Bo"], w["c"]["Mo"]
    post = bo.post(f"/api/communities/{w['community']}/posts",
                   json={"kind": "share", "title": "A questionable post", "text": text}).get_json()["post"]["id"]
    rid = ann.post("/api/reports", json={"itemType": "post", "itemId": post, "reason": "harassment"}).get_json()["reportId"]
    assert mo.post(f"/api/moderation/reports/{rid}/acknowledge").status_code == 200
    assert mo.post(f"/api/moderation/reports/{rid}/decision",
                   json={"decision": "upheld", "action": "warning", "note": "Reviewed."}).status_code in (200, 201)
    return rid


def test_clean_up_deletes_conduct_records_older_than_the_retention_setting(world, app, clock):  # TC-OR-002a
    old = _close_a_report(world)
    clock.advance(days=2)
    for n in ("Ann", "Bo", "Mo"):
        world["c"][n] = signed_in_client(app, n)  # the earlier sessions have gone idle (NFR-011)
    recent = _close_a_report(world, text="another rude post")
    root = signed_in_client(app, "Root")
    assert root.put("/api/admin/settings/LOG_RETENTION", json={"value": 1}).status_code == 200  # AC-OR-002a: 1 day
    assert one(app, "SELECT COUNT(*) FROM moderation_outcomes") == 2
    r = root.post("/api/admin/clean-up")
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["cleanUp"]["reportsDeleted"] == 1
    assert one(app, "SELECT COUNT(*) FROM safety_reports WHERE id=?", old) == 0
    assert one(app, "SELECT COUNT(*) FROM safety_reports WHERE id=?", recent) == 1
    assert one(app, "SELECT COUNT(*) FROM retention_unlock") == 0  # the append-only rule is back in force
    with app.app_context():
        assert any(e["action"] == "CLEAN_UP" for e in get_service("audit").entries())  # NFR-015
    # A moderator still cannot delete an outcome by hand (FR-067)
    conn = connect(app.config["DATABASE_PATH"])
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM moderation_outcomes WHERE report_id=?", (recent,))
    conn.close()


def test_clean_up_never_deletes_an_open_report(world, app, clock):  # OR-002 with FR-062
    ann, bo = world["c"]["Ann"], world["c"]["Bo"]
    post = bo.post(f"/api/communities/{world['community']}/posts",
                   json={"kind": "share", "title": "Still waiting", "text": "nobody looked at this"}).get_json()["post"]["id"]
    rid = ann.post("/api/reports", json={"itemType": "post", "itemId": post, "reason": "spam"}).get_json()["reportId"]
    clock.advance(days=400)
    with app.app_context():
        result = get_service("retention").run(None)
    assert result.reports_deleted == 0
    assert one(app, "SELECT COUNT(*) FROM safety_reports WHERE id=?", rid) == 1


def test_clean_up_applies_message_retention_through_the_same_run(world, app, clock):  # TC-OR-001a (via the run)
    ann, bo, ids = world["c"]["Ann"], world["c"]["Bo"], world["ids"]
    cid = ann.post("/api/connections/requests", json={"receiverId": ids["Bo"]}).get_json()["connection"]["id"]
    bo.post(f"/api/connections/{cid}/accept")
    ann.post(f"/api/messages/conversations/{cid}", json={"text": "old message"})
    clock.advance(days=121)
    with app.app_context():
        result = get_service("retention").run(None)
    assert result.messages_deleted == 1
    assert one(app, "SELECT COUNT(*) FROM messages") == 0


def test_clean_up_runs_from_the_shell(app):  # for the daily job on the pilot server
    runner = CliRunner()
    result = runner.invoke(app.cli, ["clean-up"], obj=app)
    assert result.exit_code == 0, result.output
    assert "Clean-up finished" in result.output


def test_only_administrators_can_start_a_clean_up(world):  # NFR-013
    assert world["c"]["Ann"].post("/api/admin/clean-up").status_code == 403
    assert world["c"]["Mo"].post("/api/admin/clean-up").status_code == 403
