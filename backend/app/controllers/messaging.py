"""Message endpoints (process 5.0). No rules here: each route calls one MessagingService operation."""
from flask import Blueprint, g, jsonify, request

from ..container import get_service
from ..security import profile_required

bp = Blueprint("messaging", __name__, url_prefix="/api/messages")

REFUSED = "You can only message students you are connected with."


def message_json(m, me):
    out = {"id": m.id, "text": m.body, "sentAt": m.sent_at.isoformat(), "mine": m.sender_id == me,
           "status": m.status}
    if m.status == "hidden":
        out["notice"] = "A moderator has hidden this message. Only you can see it."
    return out


def conversation_json(c, me, with_messages=False):
    out = {"connectionId": c.connection_id, "other": {"id": c.other_id, "displayName": c.other_name},
           "lastAt": c.last_at.isoformat() if c.last_at else None, "unread": c.unread}
    if with_messages:
        out["messages"] = [message_json(m, me) for m in c.messages]
    return out


@bp.get("/conversations")
@profile_required
def conversations():
    items = get_service("messaging").conversations(g.account.id)
    return jsonify({"conversations": [conversation_json(c, g.account.id) for c in items]})


@bp.get("/conversations/<int:connection_id>")
@profile_required
def open_conversation(connection_id):
    c = get_service("messaging").open(g.account.id, connection_id)
    if c is None:
        return jsonify({"message": REFUSED}), 403
    return jsonify({"conversation": conversation_json(c, g.account.id, with_messages=True)})


@bp.post("/conversations/<int:connection_id>")
@profile_required
def send(connection_id):
    result = get_service("messaging").send(g.account.id, connection_id, (request.get_json(silent=True) or {}).get("text"))
    if result.error == "not_allowed":
        return jsonify({"message": REFUSED}), 403
    if result.error == "invalid":
        return jsonify({"errors": {"text": "A message is 1 to 1000 characters."}}), 400
    return jsonify({"message": message_json(result.message, g.account.id)}), 201
