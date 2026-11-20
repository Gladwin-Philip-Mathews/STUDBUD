"""Moderation endpoints (process 6.0). No rules here: each route calls one ModerationService operation."""
from flask import Blueprint, g, jsonify, request

from ..container import get_service
from ..security import page_required, profile_required

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
@page_required("moderation")
def queue():
    return jsonify({"reports": [_queue_json(q) for q in _svc().open_queue(g.account.id)]})


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


@bp.get("/moderation/reports/<int:report_id>/context")
@page_required("moderation")
def context(report_id):
    result = _svc().report_context(g.account.id, report_id)
    if not result.ok:
        return _failed(result)
    c = result.item
    thread = c["thread"]
    if thread:
        thread = {"post": {**thread["post"], "createdAt": _iso(thread["post"]["createdAt"])},
                  "replies": [{**r, "createdAt": _iso(r["createdAt"])} for r in thread["replies"]]}
    history = [{**h, "receivedAt": _iso(h["receivedAt"])} for h in c["history"]]
    return jsonify({"context": {"reportId": c["reportId"], "reportedStudent": c["reportedStudent"],
                                "thread": thread, "history": history}})


@bp.post("/moderation/reports/<int:report_id>/acknowledge")
@page_required("moderation")
def acknowledge(report_id):
    result = _svc().acknowledge(g.account.id, report_id)
    return (jsonify({"message": "Acknowledged."}), 200) if result.ok else _failed(result)


@bp.post("/moderation/reports/<int:report_id>/decision")
@page_required("moderation")
def decide(report_id):
    d = request.get_json(silent=True) or {}
    result = _svc().decide(g.account.id, report_id, d.get("decision"), d.get("action"), d.get("note"),
                           escalate=bool(d.get("escalate", False)))
    if not result.ok:
        return _failed(result)
    out = {"message": "Decision recorded."}
    if result.case_summary is not None:  # DF-24: ready for the Office of Student Affairs
        out["message"] = "Decision recorded. The case summary for Student Affairs is ready."
        out["caseSummary"] = _summary_json(result.case_summary)
    return jsonify(out), 201


@bp.post("/moderation/reports/<int:report_id>/notes")
@page_required("moderation")
def add_note(report_id):
    result = _svc().add_later_note(g.account.id, report_id, (request.get_json(silent=True) or {}).get("note"))
    return (jsonify({"message": "Note added."}), 201) if result.ok else _failed(result)


@bp.get("/moderation/reports/<int:report_id>/summary")
@page_required("moderation")
def summary(report_id):
    result = _svc().case_summary(g.account.id, report_id)
    if not result.ok:
        return _failed(result)
    return jsonify({"summary": _summary_json(result.item)})


def _summary_json(item):
    s = dict(item)
    for key in ("receivedAt", "acknowledgedAt", "decidedAt"):
        s[key] = s[key].isoformat() if s[key] else None
    return s
