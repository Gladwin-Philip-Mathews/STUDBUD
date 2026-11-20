"""Notification endpoints (process 7.0)."""
from flask import Blueprint, g, jsonify, request

from ..container import get_service
from ..models.entities import ItemRef
from ..security import login_required, may_access

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def notification_json(n):
    return {"id": n.id, "event": n.event_type.value, "body": n.body, "createdAt": n.created_at.isoformat(),
            "read": n.read_at is not None,
            "item": {"type": n.related_item.kind, "id": n.related_item.id} if n.related_item else None}  # DR-011


@bp.get("")
@login_required
def list_notifications():
    svc = get_service("notifications")
    return jsonify({"notifications": [notification_json(n) for n in svc.list_for(g.account.id)],
                    "unread": svc.unread_count(g.account.id), "email": bool(g.account.email_notifications)})  # FR-082


@bp.get("/unread-count")
@login_required
def unread_count():
    return jsonify({"unread": get_service("notifications").unread_count(g.account.id)})


@bp.post("/<int:notification_id>/read")
@login_required
def read(notification_id):
    if not may_access(ItemRef("notification", notification_id)):  # NFR-013: a student reads only their own
        return jsonify({"message": "Not found."}), 404
    get_service("notifications").mark_read(notification_id, g.account.id)
    return jsonify({"message": "Marked as read."})


@bp.post("/read-all")
@login_required
def read_all():
    get_service("notifications").mark_all_read(g.account.id)
    return jsonify({"message": "All marked as read."})


@bp.put("/settings")
@login_required
def settings():
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("email"), bool):
        return jsonify({"message": "Send email as true or false."}), 400
    get_service("notifications").set_email_enabled(g.account.id, data["email"])
    return jsonify({"email": data["email"]})
