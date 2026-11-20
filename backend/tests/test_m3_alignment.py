"""Checks added when the code was aligned element by element with the M3 design (20 November 2026).

Each test names the diagram element it covers: CD-1a entity attributes and operations, CD-1b operations,
DFD-0 / DFD-1 flows and SD-1 messages. See docs/diagram-conformance.md.
"""
import pytest

from app.container import get_service
from app.db import connect
from app.models import Course, ItemRef
from app.models.enums import CommunityKind, ContactRange, ContentStatus, HandoffResult, PostKind
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
    conn = connect(app.config["DATABASE_PATH"])
    SqliteCourseRepository(conn).add(Course("SWEN-261", "Intro to Software Engineering"))
    conn.close()
    ids = {n: make_student(app, n) for n in ("Ann", "Bo", "Cy", "Mo", "Root")}
    sql(app, "UPDATE accounts SET role='moderator' WHERE id=?", ids["Mo"])
    sql(app, "UPDATE accounts SET role='administrator' WHERE id=?", ids["Root"])
    cl = {n: signed_in_client(app, n) for n in ids}
    for n in ("Ann", "Bo", "Cy"):
        cl[n].put("/api/profile", json=PROFILE)
    community = next(c for c in cl["Ann"].get("/api/communities").get_json()["communities"] if c["kind"] == "course")["id"]
    return {"ids": ids, "c": cl, "community": community}


def connect_pair(w, a="Ann", b="Bo"):
    cid = w["c"][a].post("/api/connections/requests", json={"receiverId": w["ids"][b]}).get_json()["connection"]["id"]
    assert w["c"][b].post(f"/api/connections/{cid}/accept").status_code == 200
    return cid


# ---------------------------------------------------------------- DR-011, D9, CD-1b notify(recipient, type, item) ----

def test_every_notification_names_the_item_it_is_about(world):  # DF-11, DF-15, DF-18, DF-26
    ids, c, community = world["ids"], world["c"], world["community"]
    cid = c["Ann"].post("/api/connections/requests", json={"receiverId": ids["Bo"]}).get_json()["connection"]["id"]
    got = c["Bo"].get("/api/notifications").get_json()["notifications"][0]
    assert got["event"] == "REQUEST_RECEIVED" and got["item"] == {"type": "connection", "id": cid}
    c["Bo"].post(f"/api/connections/{cid}/accept")
    assert c["Ann"].get("/api/notifications").get_json()["notifications"][0]["item"] == {"type": "connection", "id": cid}
    c["Ann"].post(f"/api/messages/conversations/{cid}", json={"text": "hi"})
    assert c["Bo"].get("/api/notifications").get_json()["notifications"][0]["item"] == {"type": "conversation", "id": cid}
    post = c["Ann"].post(f"/api/communities/{community}/posts",
                         json={"kind": "question", "title": "Anyone for Thursday?", "text": "Library"}).get_json()["post"]["id"]
    c["Bo"].post(f"/api/posts/{post}/replies", json={"text": "yes"})
    assert c["Ann"].get("/api/notifications").get_json()["notifications"][0]["item"] == {"type": "post", "id": post}
    rid = c["Bo"].post("/api/reports", json={"itemType": "post", "itemId": post, "reason": "spam"}).get_json()["reportId"]
    c["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    assert c["Bo"].get("/api/notifications").get_json()["notifications"][0]["item"] == {"type": "report", "id": rid}


def test_item_ref_round_trips_through_its_text_form():  # ItemRef «datatype»
    assert str(ItemRef("post", 12)) == "post:12" and ItemRef.parse("post:12") == ItemRef("post", 12)
    assert ItemRef.parse("page:moderation") == ItemRef("page", "moderation")
    assert ItemRef.parse("") is None and str(ItemRef("retention")) == "retention"


# ---------------------------------------------------------------- CD-1b AuthService.mayAccess(), NFR-013 ----

def test_may_access_refuses_another_students_conversation_notification_and_the_moderator_page(world):  # AC-NFR-013a
    c = world["c"]
    cid = connect_pair(world, "Bo", "Cy")
    c["Bo"].post(f"/api/messages/conversations/{cid}", json={"text": "between Bo and Cy"})
    assert c["Ann"].get(f"/api/messages/conversations/{cid}").status_code == 403
    assert c["Ann"].post(f"/api/messages/conversations/{cid}", json={"text": "intruding"}).status_code == 403
    bo_note = c["Cy"].get("/api/notifications").get_json()["notifications"][0]["id"]
    assert c["Ann"].post(f"/api/notifications/{bo_note}/read").status_code == 404
    assert c["Cy"].post(f"/api/notifications/{bo_note}/read").status_code == 200
    assert c["Ann"].get("/api/moderation/queue").status_code == 403
    assert c["Root"].get("/api/moderation/queue").status_code == 403  # IF-004: administrator is not a moderator
    assert c["Mo"].get("/api/admin/settings").status_code == 403
    assert c["Mo"].get("/api/moderation/queue").status_code == 200


def test_may_access_is_one_operation_on_the_auth_service(world, app):  # CD-1b
    ids = world["ids"]
    cid = connect_pair(world, "Ann", "Bo")
    with app.app_context():
        auth = get_service("auth")
        ann, cy, mo = (auth.accounts.get(ids[n]) for n in ("Ann", "Cy", "Mo"))
        assert auth.may_access(ann, ItemRef("conversation", cid)) is True
        assert auth.may_access(cy, ItemRef("conversation", cid)) is False
        assert auth.may_access(mo, ItemRef("page", "moderation")) is True
        assert auth.may_access(ann, ItemRef("page", "moderation")) is False
        assert auth.may_access(None, ItemRef("page", "moderation")) is False
        assert auth.may_access(ann, ItemRef("something-else", 1)) is False  # unknown items are refused


# ---------------------------------------------------------------- CD-1b ConnectionController.respond() ----

def test_respond_route_accepts_or_declines_with_one_flag(world):  # CD-1b, FR-044, FR-045
    ids, c = world["ids"], world["c"]
    cid = c["Ann"].post("/api/connections/requests", json={"receiverId": ids["Bo"]}).get_json()["connection"]["id"]
    assert c["Ann"].post(f"/api/connections/{cid}/respond", json={"accept": True}).status_code == 404  # receiver only
    assert c["Bo"].post(f"/api/connections/{cid}/respond", json={"accept": "yes"}).status_code == 400
    r = c["Bo"].post(f"/api/connections/{cid}/respond", json={"accept": False})
    assert r.status_code == 200 and r.get_json()["connection"]["status"] == "declined"
    note = c["Ann"].get("/api/notifications").get_json()["notifications"][0]["body"]
    assert "not accepted" in note and "declin" not in note  # FR-045


# ---------------------------------------------------------------- DFD-1 DF-23 escalation choice, DF-36, DF-24 ----

def _reported_post(w, text="rude"):
    post = w["c"]["Bo"].post(f"/api/communities/{w['community']}/posts",
                             json={"kind": "share", "title": "A questionable post", "text": text}).get_json()["post"]["id"]
    rid = w["c"]["Ann"].post("/api/reports", json={"itemType": "post", "itemId": post, "reason": "harassment"}).get_json()["reportId"]
    assert w["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge").status_code == 200
    return rid


def test_upheld_decision_with_the_escalation_choice_returns_the_case_summary(world, app):  # 6.4 to 6.6
    rid = _reported_post(world)
    r = world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/decision",
                              json={"decision": "upheld", "action": "warning", "note": "Reviewed.", "escalate": True})
    assert r.status_code == 201, r.get_json()
    summary = r.get_json()["caseSummary"]
    assert summary["reportId"] == rid and summary["decision"] == "upheld" and summary["reportedItem"]["type"] == "post"
    assert "decidedAt" in summary and summary["acknowledgedAt"] is not None
    with app.app_context():
        assert [e.item_ref for e in get_service("audit").entries("ESCALATION")] == [f"report {rid}"]


def test_a_dismissed_report_cannot_be_escalated(world):  # DF-23: escalation choice, upheld only
    rid = _reported_post(world, text="not rude at all")
    r = world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/decision",
                              json={"decision": "dismissed", "action": "none", "note": "Nothing wrong.", "escalate": True})
    assert r.status_code == 400 and "escalate" in r.get_json()["errors"]
    r = world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/decision",
                              json={"decision": "dismissed", "action": "none", "note": "Nothing wrong."})
    assert r.status_code == 201 and "caseSummary" not in r.get_json()


def test_a_conduct_decision_from_student_affairs_is_recorded_as_a_later_note(world):  # DF-25, 6.4, FR-067
    rid = _reported_post(world)
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/decision",
                          json={"decision": "upheld", "action": "warning", "note": "Reviewed."})
    r = world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/notes",
                              json={"note": "Student Affairs: warning confirmed, no further action."})
    assert r.status_code == 201
    summary = world["c"]["Mo"].get(f"/api/moderation/reports/{rid}/summary").get_json()["summary"]
    assert summary["decision"] == "upheld"


# ---------------------------------------------------------------- DF-06: the email choice travels with the profile ----

def test_email_choice_is_part_of_the_profile(world, app, gateway):  # FR-082 through process 2.0
    ids, c = world["ids"], world["c"]
    me = c["Bo"].get("/api/profile").get_json()["profile"]
    assert me["emailNotifications"] is True
    r = c["Bo"].put("/api/profile", json={**PROFILE, "emailNotifications": False})
    assert r.status_code == 200 and r.get_json()["profile"]["emailNotifications"] is False
    c["Ann"].post("/api/connections/requests", json={"receiverId": ids["Bo"]})
    from app.email_dispatch import dispatch_pending_emails
    dispatch_pending_emails(app)
    assert gateway.sent_messages() == []  # AC-FR-081b
    assert c["Bo"].get("/api/notifications").get_json()["unread"] == 1


# ---------------------------------------------------------------- CD-1a attributes and enumerations ----

def test_community_records_its_creation_time(world, app):  # D4, CD-1a Community.createdAt
    assert one(app, "SELECT COUNT(*) FROM communities WHERE created_at IS NULL") == 0
    with app.app_context():
        c = get_service("communities").communities.get(world["community"])
        assert c.created_at is not None and c.kind == CommunityKind.COURSE.value


def test_settings_are_system_setting_entities_with_their_change_time(world, app, clock):  # CD-1a SystemSetting
    root = world["c"]["Root"]
    before = {s["name"]: s for s in root.get("/api/admin/settings").get_json()["settings"]}
    assert before["OVERDUE_FLAG"]["changedAt"] is None and before["OVERDUE_FLAG"]["unit"] == "hours"
    assert root.put("/api/admin/settings/OVERDUE_FLAG", json={"value": 24}).status_code == 200
    after = {s["name"]: s for s in root.get("/api/admin/settings").get_json()["settings"]}
    assert after["OVERDUE_FLAG"]["value"] == 24 and after["OVERDUE_FLAG"]["changedAt"] is not None
    with app.app_context():
        setting = next(s for s in get_service("admin").settings.all() if s.name == "OVERDUE_FLAG")
        assert setting.changed_by == world["ids"]["Root"]


def test_audit_record_keeps_action_item_and_detail_apart(world, app):  # CD-1a AuditRecord {action, itemRef, at}
    root = world["c"]["Root"]
    root.put("/api/admin/settings/RESEND_LIMIT", json={"value": 2})
    with app.app_context():
        e = get_service("audit").entries("SETTING_CHANGED")[-1]
    assert e.action == "SETTING_CHANGED" and e.item_ref == "RESEND_LIMIT" and e.detail == "2" and e.at is not None
    assert e["action"] == e.action  # the dictionary form still works for older tests


def test_enumerations_match_the_m3_table():  # M3 section 3.2 enumeration types
    assert [k.value for k in PostKind] == ["question", "share", "study partner request"]
    assert [k.value for k in CommunityKind] == ["course", "interest"]
    assert [k.value for k in ContentStatus] == ["visible", "hidden", "deleted"]
    assert [k.value for k in ContactRange] == ["0", "1 to 2", "3 to 5", "more than 5", "skipped"]
    assert bool(HandoffResult.HANDED_OVER) and not HandoffResult.UNAVAILABLE


def test_schema_migration_adds_the_new_columns_to_an_older_database(tmp_path):  # existing laptops keep their data
    import sqlite3
    from app.db import init_db
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE notifications (id INTEGER PRIMARY KEY, recipient_id INTEGER NOT NULL, event_type TEXT NOT NULL,
          body TEXT NOT NULL, created_at TEXT NOT NULL, read_at TEXT, email_status TEXT NOT NULL DEFAULT 'not sent',
          email_resends INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE communities (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
          course_code TEXT UNIQUE, status TEXT NOT NULL DEFAULT 'active');
        CREATE TABLE audit_records (id INTEGER PRIMARY KEY, at TEXT NOT NULL, actor_id INTEGER, action TEXT NOT NULL,
          detail TEXT NOT NULL DEFAULT '');
        INSERT INTO communities(name, kind) VALUES ('Chess', 'interest');
    """)
    old.commit(); old.close()
    conn = connect(path)
    init_db(conn)
    cols = {t: {r["name"] for r in conn.execute(f"PRAGMA table_info({t})")} for t in ("notifications", "communities", "audit_records")}
    assert "related_item" in cols["notifications"] and "created_at" in cols["communities"] and "item_ref" in cols["audit_records"]
    assert conn.execute("SELECT name FROM communities").fetchone()["name"] == "Chess"
    conn.close()
