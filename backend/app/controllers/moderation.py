"""Moderation endpoints (process 6.0). No rules here: each route calls one ModerationService operation."""
from flask import Blueprint, g, jsonify, request

from ..container import get_service
from ..models.enums import Role
from ..security import profile_required, role_required

bp = Blueprint("moderation", __name__, url_prefix="/api")


def _svc():
    return get_service("moderation")


def _failed(result):
    if result.not_found:
        return jsonify({"message": "Not found."}), 404
    return jsonify({"errors": result.errors}), 400


@bp.post("/reports")
@profile_required
def submit_report():
    d = request.get_json(silent=True) or {}
    result = _svc().submit_report(g.account.id, d.get("itemType"), d.get("itemId"), d.get("reason"), d.get("text"))
    if not result.ok:
        return _failed(result)
    return jsonify({"message": "Thank you. Your report has been sent to a moderator.", "reportId": result.item.id}), 201


def _queue_json(q):
    r = q.report
    return {"id": r.id, "reason": r.reason, "text": r.text, "status": r.status, "ageHours": q.age_hours,
            "overdue": q.overdue, "receivedAt": r.received_at.isoformat(), "reporter": q.reporter_name,
            "reportedStudent": q.reported_name, "itemType": r.item_type, "item": q.item,
            "acknowledgedAt": r.acknowledged_at.isoformat() if r.acknowledged_at else None}


@bp.get("/moderation/queue")
@role_required(Role.MODERATOR)
def queue():
    return jsonify({"reports": [_queue_json(q) for q in _svc().open_queue(g.account.id)]})


@bp.post("/moderation/reports/<int:report_id>/acknowledge")
@role_required(Role.MODERATOR)
def acknowledge(report_id):
    result = _svc().acknowledge(g.account.id, report_id)
    return (jsonify({"message": "Acknowledged."}), 200) if result.ok else _failed(result)


@bp.post("/moderation/reports/<int:report_id>/decision")
@role_required(Role.MODERATOR)
def decide(report_id):
    d = request.get_json(silent=True) or {}
    result = _svc().decide(g.account.id, report_id, d.get("decision"), d.get("action"), d.get("note"))
    return (jsonify({"message": "Decision recorded."}), 201) if result.ok else _failed(result)


@bp.post("/moderation/reports/<int:report_id>/notes")
@role_required(Role.MODERATOR)
def add_note(report_id):
    result = _svc().add_later_note(g.account.id, report_id, (request.get_json(silent=True) or {}).get("note"))
    return (jsonify({"message": "Note added."}), 201) if result.ok else _failed(result)


@bp.get("/moderation/reports/<int:report_id>/summary")
@role_required(Role.MODERATOR)
def summary(report_id):
    result = _svc().case_summary(g.account.id, report_id)
    if not result.ok:
        return _failed(result)
    s = dict(result.item)
    for key in ("receivedAt", "acknowledgedAt", "decidedAt"):
        s[key] = s[key].isoformat() if s[key] else None
    return jsonify({"summary": s})
