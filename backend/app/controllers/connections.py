"""Connection endpoints (process 4.0). No rules here: each route calls one ConnectionService operation."""
from flask import Blueprint, g, jsonify, request

from ..container import get_service
from ..models.enums import RefusalReason
from ..security import profile_required

bp = Blueprint("connections", __name__, url_prefix="/api/connections")

# FR-043: a refusal never says "declined". Not available and recently declined read the same (DD-11).
REFUSAL_TEXT = {
    RefusalReason.NOTE_TOO_LONG: "The note can be up to 200 characters.",
    RefusalReason.SELF: "You cannot send a request to yourself.",
    RefusalReason.NOT_AVAILABLE: "You cannot send a request to this student right now.",
    RefusalReason.RECENTLY_DECLINED: "You cannot send a request to this student right now.",
    RefusalReason.ALREADY_CONNECTED: "You are already connected.",
    RefusalReason.PENDING_EXISTS: "A request is already pending between you.",
}


def connection_json(c, other=None):
    out = {"id": c.id, "status": c.status.value, "note": c.note,
           "createdAt": c.created_at.isoformat(), "statusChangedAt": c.status_changed_at.isoformat()}
    if other is not None:
        out["other"] = {"id": other.id, "displayName": other.display_name}
    return out


@bp.post("/requests")
@profile_required
def send_request():
    data = request.get_json(silent=True) or {}
    receiver_id = data.get("receiverId")
    if not isinstance(receiver_id, int):
        return jsonify({"message": "Choose a student."}), 400
    result = get_service("connections").send_request(g.account.id, receiver_id, data.get("note") or "")
    if result.refusal:
        return jsonify({"reason": result.refusal.value, "message": REFUSAL_TEXT[result.refusal]}), 400
    return jsonify({"connection": connection_json(result.connection)}), 201


@bp.get("")
@profile_required
def accepted():
    return jsonify({"connections": get_service("connections").accepted_for(g.account.id)})


@bp.get("/incoming")
@profile_required
def incoming():
    return jsonify({"requests": [connection_json(c, o) for c, o in get_service("connections").incoming(g.account.id)]})


@bp.get("/outgoing")
@profile_required
def outgoing():
    return jsonify({"requests": [connection_json(c, o) for c, o in get_service("connections").outgoing(g.account.id)]})


def _answer(action):
    c = getattr(get_service("connections"), action)(int(request.view_args["connection_id"]), g.account.id)
    if c is None:
        return jsonify({"message": "That request is not available."}), 404
    return jsonify({"connection": connection_json(c)}), 200


@bp.post("/<int:connection_id>/accept")
@profile_required
def accept(connection_id):
    return _answer("accept")


@bp.post("/<int:connection_id>/decline")
@profile_required
def decline(connection_id):
    return _answer("decline")


@bp.post("/<int:connection_id>/respond")
@profile_required
def respond(connection_id):
    """CD-1b ConnectionController.respond(session, connectionId, accept): one route for accept and decline."""
    accept = (request.get_json(silent=True) or {}).get("accept")
    if not isinstance(accept, bool):
        return jsonify({"message": "Send accept as true or false."}), 400
    c = get_service("connections").respond(connection_id, g.account.id, accept)
    if c is None:
        return jsonify({"message": "Not found."}), 404
    return jsonify({"connection": connection_json(c), "message": "Accepted." if accept else "Not accepted."})


@bp.post("/<int:connection_id>/withdraw")
@profile_required
def withdraw(connection_id):
    return _answer("withdraw")


@bp.post("/<int:connection_id>/remove")
@profile_required
def remove(connection_id):
    return _answer("remove")


@bp.get("/suggestions")
@profile_required
def suggestions():
    items = get_service("connections").suggestions(g.account.id)
    return jsonify({"suggestions": [
        {"accountId": s.account_id, "displayName": s.display_name, "intent": s.intent,
         "sharedCourses": s.shared_courses, "sharedInterests": s.shared_interests} for s in items]})


@bp.post("/suggestions/<int:account_id>/dismiss")
@profile_required
def dismiss(account_id):
    get_service("connections").dismiss_suggestion(g.account.id, account_id)
    return jsonify({"message": "Dismissed."}), 200
