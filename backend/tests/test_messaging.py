from datetime import timedelta

import pytest

from app.container import get_service

from .helpers import make_student, signed_in_client


def connect(a_client, b_client, b_id):
    cid = a_client.post("/api/connections/requests", json={"receiverId": b_id}).get_json()["connection"]["id"]
    assert b_client.post(f"/api/connections/{cid}/accept").status_code == 200
    return cid


@pytest.fixture
def trio(app):
    ids = {n: make_student(app, n) for n in ("Ana", "Ben", "Cat")}
    cl = {n: signed_in_client(app, n) for n in ids}
    return ids, cl


def send(client, cid, text="Library at 4?"):
    return client.post(f"/api/messages/conversations/{cid}", json={"text": text})


def test_message_is_delivered_and_the_receiver_is_notified(trio):  # AC-FR-050a
    ids, cl = trio
    cid = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    assert send(cl["Ana"], cid).status_code == 201
    seen = cl["Ben"].get(f"/api/messages/conversations/{cid}").get_json()["conversation"]["messages"]
    assert [m["text"] for m in seen] == ["Library at 4?"]
    notes = cl["Ben"].get("/api/notifications").get_json()["notifications"]
    assert any("sent you a message" in n["body"] and "Library" not in n["body"] for n in notes)  # FR-081: no text


def test_length_limits(trio):  # FR-050
    ids, cl = trio
    cid = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    assert send(cl["Ana"], cid, "x" * 1000).status_code == 201
    assert send(cl["Ana"], cid, "x" * 1001).status_code == 400
    assert send(cl["Ana"], cid, "   ").status_code == 400


def test_refused_unless_connection_is_accepted_and_nothing_is_stored(trio, app):  # AC-FR-051a
    ids, cl = trio
    pending = cl["Ana"].post("/api/connections/requests", json={"receiverId": ids["Cat"]}).get_json()["connection"]["id"]
    assert send(cl["Ana"], pending).status_code == 403  # pending
    cid = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    assert send(cl["Cat"], cid).status_code == 403  # not part of the connection
    assert cl["Cat"].get(f"/api/messages/conversations/{cid}").status_code == 403  # cannot read it either
    assert send(cl["Ana"], 9999).status_code == 403
    cl["Ana"].post(f"/api/connections/{cid}/remove")
    assert send(cl["Ana"], cid).status_code == 403  # removed
    with app.app_context():
        assert get_service("messaging").messages.for_connection(pending) == []


def test_conversations_most_recent_first_with_unread_count(trio, clock):  # AC-FR-052a
    ids, cl = trio
    old = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    new = connect(cl["Ana"], cl["Cat"], ids["Cat"])
    send(cl["Ben"], old, "first")
    clock.advance(minutes=5)
    send(cl["Cat"], new, "second")
    order = cl["Ana"].get("/api/messages/conversations").get_json()["conversations"]
    assert [c["connectionId"] for c in order] == [new, old]
    clock.advance(minutes=5)
    send(cl["Ben"], old, "third")  # the older conversation moves to the top with 1 new message
    top = cl["Ana"].get("/api/messages/conversations").get_json()["conversations"][0]
    assert top["connectionId"] == old and top["unread"] == 2
    cl["Ana"].get(f"/api/messages/conversations/{old}")  # opening clears it
    top = next(c for c in cl["Ana"].get("/api/messages/conversations").get_json()["conversations"] if c["connectionId"] == old)
    assert top["unread"] == 0


def test_messages_are_in_time_order(trio, clock):  # FR-052
    ids, cl = trio
    cid = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    for text in ("one", "two", "three"):
        send(cl["Ana"], cid, text)
        clock.advance(seconds=30)
    got = cl["Ben"].get(f"/api/messages/conversations/{cid}").get_json()["conversation"]["messages"]
    assert [m["text"] for m in got] == ["one", "two", "three"]


def test_hidden_message_shows_only_to_its_sender(trio, app):  # FR-065
    ids, cl = trio
    cid = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    mid = send(cl["Ana"], cid).get_json()["message"]["id"]
    with app.app_context():
        repo = get_service("messaging").messages
        m = repo.get(mid)
        m.hide()
        repo.save(m)
    assert cl["Ben"].get(f"/api/messages/conversations/{cid}").get_json()["conversation"]["messages"] == []
    mine = cl["Ana"].get(f"/api/messages/conversations/{cid}").get_json()["conversation"]["messages"]
    assert "hidden" in mine[0]["notice"]


def test_deleting_the_account_removes_its_messages(trio, app):  # FR-015
    from .helpers import PASSWORD
    ids, cl = trio
    cid = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    send(cl["Ana"], cid)
    assert cl["Ana"].delete("/api/profile", json={"password": PASSWORD}).status_code == 200
    with app.app_context():
        assert get_service("messaging").messages.for_connection(cid) == []


def test_retention_deletes_old_messages_but_keeps_protected_ones(trio, app, clock):  # OR-001
    ids, cl = trio
    cid = connect(cl["Ana"], cl["Ben"], ids["Ben"])
    old = send(cl["Ana"], cid, "old").get_json()["message"]["id"]
    kept = send(cl["Ana"], cid, "attached to a report").get_json()["message"]["id"]
    clock.advance(days=121)
    send(signed_in_client(app, "Ana"), cid, "recent")  # a new sign in: the old session has expired
    with app.app_context():
        svc = get_service("messaging")
        assert svc.apply_retention(keep_ids={kept}) == 1
        assert [m.body for m in svc.messages.for_connection(cid)] == ["attached to a report", "recent"]
