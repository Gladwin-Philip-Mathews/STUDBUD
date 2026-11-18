import pytest

from app.container import get_service
from app.db import connect
from app.models import Course
from app.repositories import SqliteCourseRepository

from .helpers import PASSWORD, make_student, signed_in_client

PROFILE = {"intent": "both", "cohort": "first year", "interests": [], "courses": ["SWEN-261"]}


def sql(app, query, *args):
    conn = connect(app.config["DATABASE_PATH"])
    conn.execute(query, args)
    conn.commit()
    conn.close()


@pytest.fixture
def world(app):
    """Ann reports Bo. Mo is a moderator. Ann and Bo share a course community and are connected."""
    conn = connect(app.config["DATABASE_PATH"])
    SqliteCourseRepository(conn).add(Course("SWEN-261", "Intro to Software Engineering"))
    conn.close()
    ids = {n: make_student(app, n) for n in ("Ann", "Bo", "Mo", "Cy")}
    sql(app, "UPDATE accounts SET role='moderator' WHERE id=?", ids["Mo"])
    cl = {n: signed_in_client(app, n) for n in ids}
    for n in ("Ann", "Bo"):
        cl[n].put("/api/profile", json=PROFILE)
    community = next(c for c in cl["Ann"].get("/api/communities").get_json()["communities"] if c["kind"] == "course")["id"]
    post = cl["Bo"].post(f"/api/communities/{community}/posts",
                         json={"kind": "share", "title": "A questionable post", "text": "Something rude"}).get_json()["post"]["id"]
    reply = cl["Bo"].post(f"/api/posts/{post}/replies", json={"text": "a rude reply"}).get_json()["reply"]["id"]
    conn_id = cl["Ann"].post("/api/connections/requests", json={"receiverId": ids["Bo"]}).get_json()["connection"]["id"]
    cl["Bo"].post(f"/api/connections/{conn_id}/accept")
    msg = cl["Bo"].post(f"/api/messages/conversations/{conn_id}", json={"text": "a private threat"}).get_json()["message"]["id"]
    return {"ids": ids, "c": cl, "post": post, "reply": reply, "msg": msg, "conn": conn_id}


def report(client, item_type, item_id, reason="harassment", text=""):
    return client.post("/api/reports", json={"itemType": item_type, "itemId": item_id, "reason": reason, "text": text})


def queue(w):
    return w["c"]["Mo"].get("/api/moderation/queue").get_json()["reports"]


def decide(w, rid, decision="upheld", action="warning", note="Reviewed."):
    return w["c"]["Mo"].post(f"/api/moderation/reports/{rid}/decision",
                             json={"decision": decision, "action": action, "note": note})


def make_report(w, kind="post", **kw):
    item = {"post": w["post"], "reply": w["reply"], "message": w["msg"], "student": w["ids"]["Bo"]}[kind]
    return report(w["c"]["Ann"], kind, item, **kw).get_json()["reportId"]


def test_report_records_reporter_item_reason_and_appears_in_the_queue(world):  # AC-FR-060a, AC-FR-061a
    r = report(world["c"]["Ann"], "post", world["post"])
    assert r.status_code == 201 and "reportId" in r.get_json()
    q = queue(world)
    assert len(q) == 1 and q[0]["reason"] == "harassment" and q[0]["reporter"] == "Ann" and q[0]["reportedStudent"] == "Bo"


def test_report_text_limit_and_reason_required(world):  # AC-FR-060b, FR-069
    assert report(world["c"]["Ann"], "post", world["post"], text="x" * 501).status_code == 400
    assert report(world["c"]["Ann"], "post", world["post"], text="x" * 500).status_code == 201
    r = report(world["c"]["Ann"], "post", world["post"], reason="")
    assert r.status_code == 400 and "reason" in r.get_json()["errors"]


def test_cannot_report_yourself_but_two_reports_on_one_item_are_kept(world):  # AC-FR-069a
    own = report(world["c"]["Bo"], "post", world["post"])
    assert own.status_code == 400 and "item" in own.get_json()["errors"]
    world["c"]["Cy"].put("/api/profile", json={**PROFILE, "courses": []})
    assert report(world["c"]["Ann"], "post", world["post"]).status_code == 201
    assert report(world["c"]["Ann"], "post", world["post"], reason="spam").status_code == 201  # second report on the item
    assert len(queue(world)) == 2


def test_can_report_a_student_a_reply_and_a_message(world):  # FR-060, FR-053
    for kind, item in (("student", world["ids"]["Bo"]), ("reply", world["reply"]), ("message", world["msg"])):
        assert report(world["c"]["Ann"], kind, item).status_code == 201
    assert report(world["c"]["Cy"], "message", world["msg"]).status_code == 404  # not their conversation


def test_queue_is_oldest_first_and_flags_overdue(world, app, clock):  # AC-FR-062a
    def new_report():
        world["c"]["Ann"] = signed_in_client(app, "Ann")  # the 2 hour session limit applies to the shifted clock
        return make_report(world)

    first = new_report()
    clock.advance(hours=4)
    second = new_report()
    clock.advance(hours=6)
    third = new_report()
    clock.advance(hours=30)  # ages: 40, 36 and 30 hours
    world["c"]["Mo"] = signed_in_client(app, "Mo")
    q = queue(world)
    assert [r["id"] for r in q] == [first, second, third]
    assert [r["overdue"] for r in q] == [True, True, False]


def test_only_moderators_reach_the_queue(world):  # IF-004, NFR-013
    assert world["c"]["Ann"].get("/api/moderation/queue").status_code == 403
    assert world["c"]["Ann"].post("/api/moderation/reports/1/acknowledge").status_code == 403


def test_acknowledgement_notifies_and_keeps_the_report_open(world):  # AC-FR-063a
    rid = make_report(world)
    assert world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge").status_code == 200
    q = queue(world)
    assert len(q) == 1 and q[0]["status"] == "acknowledged" and q[0]["acknowledgedAt"]
    assert any("received" in n["body"] for n in world["c"]["Ann"].get("/api/notifications").get_json()["notifications"])
    first = q[0]["acknowledgedAt"]
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")  # a second acknowledgement changes nothing
    assert queue(world)[0]["acknowledgedAt"] == first
    received = [n for n in world["c"]["Ann"].get("/api/notifications").get_json()["notifications"] if "received" in n["body"]]
    assert len(received) == 1  # not notified twice


def test_decision_needs_decision_action_and_note(world):  # AC-FR-064a
    rid = make_report(world)
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    r = decide(world, rid, note="")
    assert r.status_code == 400 and "note" in r.get_json()["errors"]
    assert decide(world, rid, action=None).status_code == 400
    assert decide(world, rid, decision=None).status_code == 400
    assert decide(world, rid, decision="dismissed", action="warning").status_code == 400
    assert decide(world, rid).status_code == 201
    assert queue(world) == []  # closed reports leave the queue


def test_decide_requires_acknowledgement_first(world):
    rid = make_report(world)
    assert decide(world, rid).status_code == 400


def test_closing_tells_the_reporter_without_the_action_or_name(world):  # AC-FR-068a
    rid = make_report(world)
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    decide(world, rid, action="account suspended")
    bodies = [n["body"] for n in world["c"]["Ann"].get("/api/notifications").get_json()["notifications"]]
    closed = next(b for b in bodies if "closed" in b)
    assert closed == "Your report was reviewed and closed." and "Bo" not in closed and "suspend" not in closed


def test_closed_decision_cannot_change_but_a_dated_note_can_be_added(world, app):  # AC-FR-067a
    rid = make_report(world)
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    decide(world, rid)
    assert decide(world, rid, decision="dismissed", action="none").status_code == 400
    assert world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/notes", json={"note": "Student Affairs agreed."}).status_code == 201
    with app.app_context():
        outcome = get_service("moderation").get_outcome(rid)
        assert outcome.decision == "upheld" and outcome.later_notes[0][0] == "Student Affairs agreed."
    with pytest.raises(Exception):  # the log refuses edits and deletes even from SQL
        sql(app, "UPDATE moderation_outcomes SET decision='dismissed' WHERE report_id=?", rid)
    with pytest.raises(Exception):
        sql(app, "DELETE FROM moderation_outcomes WHERE report_id=?", rid)


def test_hidden_content_is_removed_from_others_but_author_sees_a_notice(world):  # AC-FR-065a
    rid = make_report(world, "reply")
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    assert decide(world, rid, action="content hidden").status_code == 201
    seen_by_ann = world["c"]["Ann"].get(f"/api/posts/{world['post']}").get_json()["post"]["replies"]
    assert seen_by_ann == []
    seen_by_bo = world["c"]["Bo"].get(f"/api/posts/{world['post']}").get_json()["post"]["replies"]
    assert "hidden" in seen_by_bo[0]["notice"]


def test_hidden_message_is_removed_for_the_receiver(world):  # FR-065
    rid = make_report(world, "message")
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    decide(world, rid, action="content hidden")
    got = world["c"]["Ann"].get(f"/api/messages/conversations/{world['conn']}").get_json()["conversation"]["messages"]
    assert got == []


def test_suspension_ends_the_session_refuses_sign_in_and_hides_from_suggestions(world, app):  # AC-FR-066a
    rid = make_report(world)
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    decide(world, rid, action="account suspended")
    assert world["c"]["Bo"].get("/api/connections/incoming").status_code == 401  # next request refused
    r = app.test_client().post("/api/auth/sign-in", json={"email": "bo@g.rit.edu", "password": PASSWORD})
    assert r.status_code == 403 and "conduct policy" in r.get_json()["message"] and "Student Affairs" in r.get_json()["message"]
    cy = signed_in_client(app, "Cy")
    cy.put("/api/profile", json={**PROFILE, "courses": []})
    assert "Bo" not in [s["displayName"] for s in cy.get("/api/connections/suggestions").get_json()["suggestions"]]


def test_moderator_sees_message_text_only_through_a_report_and_each_access_is_logged(world, app):  # FR-054
    assert queue(world) == []
    rid = make_report(world, "message")
    q = queue(world)
    assert q[0]["item"]["text"] == "a private threat"
    queue(world)  # opened again: logged again
    with app.app_context():
        entries = get_service("audit").entries("MESSAGE_ACCESS")
    assert len(entries) == 2 and f"report {rid}" in entries[0]["detail"]


def test_decision_is_written_to_the_audit_record(world, app):  # NFR-015
    rid = make_report(world)
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    decide(world, rid)
    with app.app_context():
        assert [e["action"] for e in get_service("audit").entries("DECISION")] == ["DECISION"]


def test_case_summary_only_for_upheld_and_has_no_other_messages(world):  # AC-FR-070a
    rid = make_report(world, "message")
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid}/acknowledge")
    assert world["c"]["Mo"].get(f"/api/moderation/reports/{rid}/summary").status_code == 400  # not decided yet
    decide(world, rid, decision="upheld", action="warning")
    s = world["c"]["Mo"].get(f"/api/moderation/reports/{rid}/summary").get_json()["summary"]
    assert {"reason", "decision", "receivedAt", "decidedAt", "reportedItem"} <= set(s)
    assert s["reportedItem"]["text"] == "a private threat"
    rid2 = make_report(world)
    world["c"]["Mo"].post(f"/api/moderation/reports/{rid2}/acknowledge")
    decide(world, rid2, decision="dismissed", action="none")
    assert world["c"]["Mo"].get(f"/api/moderation/reports/{rid2}/summary").status_code == 400


def test_deleted_post_stays_visible_to_the_moderator(world):  # FR-033
    rid = make_report(world)
    world["c"]["Bo"].delete(f"/api/posts/{world['post']}")
    assert queue(world)[0]["item"]["text"] == "Something rude"


def test_retention_keeps_messages_named_in_open_reports(world, app, clock):  # OR-001
    make_report(world, "message")
    clock.advance(days=200)
    with app.app_context():
        keep = get_service("moderation").retention_keep_ids()
        assert world["msg"] in keep
        assert get_service("messaging").apply_retention(keep) == 0
