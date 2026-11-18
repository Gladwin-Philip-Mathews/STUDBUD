from datetime import timedelta

import pytest

from app.email_dispatch import dispatch_pending_emails
from app.models import AccountStatus, Profile

from .helpers import make_student, signed_in_client


@pytest.fixture
def pair(app):
    a, b = make_student(app, "Ana"), make_student(app, "Ben")
    return a, b, signed_in_client(app, "Ana"), signed_in_client(app, "Ben")


def send(client, receiver_id, note=""):
    return client.post("/api/connections/requests", json={"receiverId": receiver_id, "note": note})


def test_request_is_pending_and_receiver_is_notified(pair):  # AC-FR-042a
    a, b, ana, ben = pair
    r = send(ana, b, "x" * 200)
    assert r.status_code == 201 and r.get_json()["connection"]["status"] == "pending"
    notes = ben.get("/api/notifications").get_json()
    assert notes["unread"] == 1 and "Ana" in notes["notifications"][0]["body"]


def test_note_over_200_characters_is_rejected(pair):  # AC-FR-042b
    a, b, ana, ben = pair
    r = send(ana, b, "x" * 201)
    assert r.status_code == 400 and r.get_json()["reason"] == "NOTE_TOO_LONG"


def test_refusal_rules_apply_in_order(pair, app):  # SD-1 M14/M15
    a, b, ana, ben = pair
    assert send(ana, a, "x" * 201).get_json()["reason"] == "NOTE_TOO_LONG"  # note before self
    assert send(ana, a).get_json()["reason"] == "SELF"
    assert send(ana, 9999).get_json()["reason"] == "NOT_AVAILABLE"
    make_student(app, "Cleo", status=AccountStatus.SUSPENDED)
    make_student(app, "Dan", status=AccountStatus.UNVERIFIED)
    assert send(ana, 3).get_json()["reason"] == "NOT_AVAILABLE"
    assert send(ana, 4).get_json()["reason"] == "NOT_AVAILABLE"


def test_pending_in_either_direction_and_already_connected(pair):
    a, b, ana, ben = pair
    send(ana, b)
    assert send(ana, b).get_json()["reason"] == "PENDING_EXISTS"
    assert send(ben, a).get_json()["reason"] == "PENDING_EXISTS"
    cid = ben.get("/api/connections/incoming").get_json()["requests"][0]["id"]
    ben.post(f"/api/connections/{cid}/accept")
    assert send(ana, b).get_json()["reason"] == "ALREADY_CONNECTED"
    assert send(ben, a).get_json()["reason"] == "ALREADY_CONNECTED"


def test_recent_decline_blocks_for_30_days_without_saying_declined(pair, clock, app):  # AC-FR-043a
    a, b, ana, ben = pair
    send(ana, b)
    cid = ben.get("/api/connections/incoming").get_json()["requests"][0]["id"]
    ben.post(f"/api/connections/{cid}/decline")
    r = send(ana, b)
    assert r.status_code == 400 and "declin" not in r.get_json()["message"].lower()
    other = send(ana, 9999)  # same text as a student who is not available (DD-11)
    assert r.get_json()["message"] == other.get_json()["message"]
    clock.advance(days=29)
    ana = signed_in_client(app, "Ana")  # the old session ended after 2 idle hours (NFR-011)
    assert send(ana, b).status_code == 400
    clock.advance(days=2)
    ana = signed_in_client(app, "Ana")
    assert send(ana, b).status_code == 201


def test_accept_lists_both_and_notifies_requester(pair):  # AC-FR-044a
    a, b, ana, ben = pair
    send(ana, b)
    cid = ben.get("/api/connections/incoming").get_json()["requests"][0]["id"]
    assert ben.post(f"/api/connections/{cid}/accept").status_code == 200
    assert [c["displayName"] for c in ana.get("/api/connections").get_json()["connections"]] == ["Ben"]
    assert [c["displayName"] for c in ben.get("/api/connections").get_json()["connections"]] == ["Ana"]
    assert "accepted" in ana.get("/api/notifications").get_json()["notifications"][0]["body"]


def test_decline_tells_requester_only_not_accepted(pair):  # AC-FR-045a
    a, b, ana, ben = pair
    send(ana, b)
    cid = ben.get("/api/connections/incoming").get_json()["requests"][0]["id"]
    ben.post(f"/api/connections/{cid}/decline")
    body = ana.get("/api/notifications").get_json()["notifications"][0]["body"]
    assert body == "Your connection request was not accepted."
    assert ana.get("/api/connections").get_json()["connections"] == []


def test_withdraw_removes_request_for_receiver(pair):  # FR-046
    a, b, ana, ben = pair
    cid = send(ana, b).get_json()["connection"]["id"]
    assert ana.post(f"/api/connections/{cid}/withdraw").status_code == 200
    assert ben.get("/api/connections/incoming").get_json()["requests"] == []


def test_remove_ends_connection_for_both(pair):  # AC-FR-048a
    a, b, ana, ben = pair
    cid = send(ana, b).get_json()["connection"]["id"]
    ben.post(f"/api/connections/{cid}/accept")
    assert ana.post(f"/api/connections/{cid}/remove").status_code == 200
    assert ana.get("/api/connections").get_json()["connections"] == []
    assert ben.get("/api/connections").get_json()["connections"] == []


def test_only_the_receiver_can_answer_and_only_the_sender_can_withdraw(pair):
    a, b, ana, ben = pair
    cid = send(ana, b).get_json()["connection"]["id"]
    assert ana.post(f"/api/connections/{cid}/accept").status_code == 404
    assert ben.post(f"/api/connections/{cid}/withdraw").status_code == 404


def test_requests_need_sign_in(app):
    assert app.test_client().post("/api/connections/requests", json={"receiverId": 1}).status_code == 401


# ---- notifications and email (FR-080 to FR-084) ----
def test_notification_list_newest_first_read_and_read_all(pair):  # FR-083
    a, b, ana, ben = pair
    send(ana, b)
    cid = ben.get("/api/connections/incoming").get_json()["requests"][0]["id"]
    ben.post(f"/api/connections/{cid}/remove")  # no-op, not accepted
    nid = ben.get("/api/notifications").get_json()["notifications"][0]["id"]
    assert ben.post(f"/api/notifications/{nid}/read").status_code == 200
    assert ben.get("/api/notifications/unread-count").get_json()["unread"] == 0
    send(ana, 9999)  # refused, no notification
    assert ben.post("/api/notifications/read-all").status_code == 200


def test_cannot_read_someone_elses_notification(pair):
    a, b, ana, ben = pair
    send(ana, b)
    nid = ben.get("/api/notifications").get_json()["notifications"][0]["id"]
    assert ana.post(f"/api/notifications/{nid}/read").status_code == 404


def test_email_names_the_sender_and_is_sent_after_the_request(pair, app, gateway):  # AC-FR-081a
    a, b, ana, ben = pair
    send(ana, b, "private note")
    assert gateway.sent == []  # nothing yet: the email goes out after the response
    assert dispatch_pending_emails(app) == 1
    assert len(gateway.sent) == 1
    mail = gateway.sent[0]
    assert mail.to == "ben@g.rit.edu" and "Ana" in mail.body and "private note" not in mail.body
    assert dispatch_pending_emails(app) == 0  # not sent twice


def test_no_email_when_switched_off_but_in_app_stays(pair, app, gateway):  # AC-FR-081b, FR-082
    a, b, ana, ben = pair
    assert ben.put("/api/notifications/settings", json={"email": False}).status_code == 200
    send(ana, b)
    dispatch_pending_emails(app)
    assert gateway.sent == []
    assert ben.get("/api/notifications").get_json()["unread"] == 1


def test_undelivered_email_is_attempted_at_most_four_times(pair, app, gateway):  # AC-FR-084a, CH-15
    a, b, ana, ben = pair
    gateway.available = False
    send(ana, b)
    for _ in range(8):
        dispatch_pending_emails(app)
    assert gateway.attempts == 4
    assert ben.get("/api/notifications").get_json()["unread"] == 1  # in-app notification stays


def test_email_is_handed_over_after_response_in_production_mode(app, gateway):
    app.config["EMAIL_DISPATCH"] = "after_response"
    a, b = make_student(app, "Ana"), make_student(app, "Ben")
    ana = signed_in_client(app, "Ana")
    response = send(ana, b)
    response.close()  # the server closes the response after sending it
    assert len(gateway.sent) == 1


# ---- suggestions (FR-040, FR-041) ----
def student_with(app, name, intent="both", courses=(), interests=()):
    return make_student(app, name, profile=Profile(0, intent=intent, course_codes=list(courses), interests=list(interests)))


def test_suggestions_ordered_by_shared_items_and_show_only_allowed_fields(app):
    me = student_with(app, "Me", "study partner", ["SWEN-261", "MATH-101"], ["chess"])
    two = student_with(app, "Two", "study partner", ["SWEN-261"], ["Chess"])
    one = student_with(app, "One", "both", ["MATH-101"])
    student_with(app, "None", "study partner", ["ART-100"])  # shares nothing
    student_with(app, "Friend", "friendship", ["SWEN-261"])  # different intent
    client = signed_in_client(app, "Me")
    got = client.get("/api/connections/suggestions").get_json()["suggestions"]
    assert [s["displayName"] for s in got] == ["Two", "One"]
    assert set(got[0]) == {"accountId", "displayName", "intent", "sharedCourses", "sharedInterests"}
    assert got[0]["sharedInterests"] == ["chess"]


def test_suggestions_exclude_connected_pending_declined_and_dismissed(app):
    me = student_with(app, "Me", "both", ["C1"])
    ids = {n: student_with(app, n, "both", ["C1"]) for n in ("Pend", "Conn", "Decl", "Dism", "Keep")}
    client = signed_in_client(app, "Me")
    send(client, ids["Pend"]); send(client, ids["Conn"])
    conn_client = signed_in_client(app, "Conn")
    cid = conn_client.get("/api/connections/incoming").get_json()["requests"][0]["id"]
    conn_client.post(f"/api/connections/{cid}/accept")
    send(client, ids["Decl"])  # Me asks Decl, and Decl declines
    cid = signed_in_client(app, "Decl").get("/api/connections/incoming").get_json()["requests"][0]["id"]
    signed_in_client(app, "Decl").post(f"/api/connections/{cid}/decline")
    client.post(f"/api/connections/suggestions/{ids['Dism']}/dismiss")
    got = [s["displayName"] for s in client.get("/api/connections/suggestions").get_json()["suggestions"]]
    assert got == ["Keep"]


def test_suggestions_limited_to_ten(app):
    student_with(app, "Me", "both", ["C1"])
    for i in range(12):
        student_with(app, f"S{i:02d}", "both", ["C1"])
    got = signed_in_client(app, "Me").get("/api/connections/suggestions").get_json()["suggestions"]
    assert len(got) == 10


def test_returned_status_triggers_resend_up_to_three_times(pair, app, gateway):  # SD-1 M32 to M35, AC-FR-084a
    from app.container import get_service
    from app.models.enums import EmailStatus
    a, b, ana, ben = pair
    send(ana, b)
    dispatch_pending_emails(app)  # first handoff
    assert gateway.attempts == 1
    with app.app_context():
        notes = get_service("notifications")
        n_id = notes.list_for(b)[0].id
        for _ in range(5):  # the mail route keeps returning it
            notes.on_delivery_status(n_id, EmailStatus.RETURNED)
    assert gateway.attempts == 4  # one handoff plus three resends, never more


def test_respond_accepts_or_declines_for_the_receiver(pair, app):  # CD-1a respond()
    from app.container import get_service
    from app.models.enums import ConnectionStatus
    a, b, ana, ben = pair
    send(ana, b)
    with app.app_context():
        svc = get_service("connections")
        cid = svc.connections.for_account(b)[0].id
        assert svc.respond(cid, a, accept=True) is None  # only the receiver can answer
        assert svc.respond(cid, b, accept=True).status == ConnectionStatus.ACCEPTED
