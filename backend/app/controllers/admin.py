"""Administration endpoints (process 9.0) and the pilot report (8.0). No rules here: each route calls one service operation."""
import dataclasses

from flask import Blueprint, Response, g, jsonify, request

from ..container import get_service
from ..security import page_required

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _svc():
    return get_service("admin")


def _body():
    return request.get_json(silent=True) or {}


def _failed(result):
    if result.not_found:
        return jsonify({"message": "Not found."}), 404
    return jsonify({"errors": result.errors}), 400


def course_json(c):
    return {"code": c.code, "title": c.name, "status": c.status}


@bp.get("/status")
@page_required("admin")
def status():
    return jsonify({"status": _svc().status()})


@bp.get("/courses")
@page_required("admin")
def courses():
    return jsonify({"courses": [course_json(c) for c in _svc().list_courses()]})


@bp.post("/courses")
@page_required("admin")
def add_course():
    r = _svc().add_course(g.account.id, _body().get("code"), _body().get("title"))
    return (jsonify({"course": course_json(r.item)}), 201) if r.ok else _failed(r)


@bp.put("/courses/<code>")
@page_required("admin")
def rename_course(code):
    r = _svc().rename_course(g.account.id, code, _body().get("title"))
    return (jsonify({"course": course_json(r.item)}), 200) if r.ok else _failed(r)


@bp.post("/courses/<code>/archive")
@page_required("admin")
def archive_course(code):
    r = _svc().archive_course(g.account.id, code)
    return (jsonify({"course": course_json(r.item)}), 200) if r.ok else _failed(r)


@bp.post("/courses/import")
@page_required("admin")
def import_courses():
    r = _svc().import_courses(g.account.id, _body().get("csv"))
    message = f"{len(r.added)} courses added."
    if r.duplicates:
        message += f" Not added because the code is already on the list: {', '.join(r.duplicates)}."
    if r.invalid:
        message += f" Not added because the row is not valid: {', '.join(r.invalid)}."
    return jsonify({"added": r.added, "duplicates": r.duplicates, "invalid": r.invalid, "message": message})


@bp.get("/domains")
@page_required("admin")
def domains():
    return jsonify({"domains": [{"domain": d.domain, "addedAt": d.added_at.isoformat() if d.added_at else None}
                                for d in _svc().list_domains()]})


@bp.post("/domains")
@page_required("admin")
def add_domain():
    r = _svc().add_domain(g.account.id, _body().get("domain"))
    return (jsonify({"domain": r.item.domain}), 201) if r.ok else _failed(r)


@bp.delete("/domains/<domain>")
@page_required("admin")
def remove_domain(domain):
    r = _svc().remove_domain(g.account.id, domain)
    return (jsonify({"message": "Removed."}), 200) if r.ok else _failed(r)


@bp.post("/communities")
@page_required("admin")
def create_community():
    r = _svc().create_interest_community(g.account.id, _body().get("name"))
    return (jsonify({"community": {"id": r.item.id, "name": r.item.name}}), 201) if r.ok else _failed(r)


@bp.get("/interest-suggestions")
@page_required("admin")
def interest_suggestions():
    return jsonify({"suggestions": _svc().list_suggestions()})


@bp.post("/interest-suggestions/<int:suggestion_id>/create")
@page_required("admin")
def create_from_suggestion(suggestion_id):
    r = _svc().create_from_suggestion(g.account.id, suggestion_id)
    return (jsonify({"community": {"id": r.item.id, "name": r.item.name}}), 201) if r.ok else _failed(r)


@bp.post("/interest-suggestions/<int:suggestion_id>/dismiss")
@page_required("admin")
def dismiss_suggestion(suggestion_id):
    r = _svc().dismiss_suggestion(g.account.id, suggestion_id)
    return (jsonify({"message": "Dismissed."}), 200) if r.ok else _failed(r)


@bp.put("/communities/<int:community_id>")
@page_required("admin")
def rename_community(community_id):
    r = _svc().rename_community(g.account.id, community_id, _body().get("name"))
    return (jsonify({"community": {"id": r.item.id, "name": r.item.name}}), 200) if r.ok else _failed(r)


@bp.post("/communities/<int:community_id>/archive")
@page_required("admin")
def archive_community(community_id):
    r = _svc().archive_community(g.account.id, community_id)
    return (jsonify({"message": "Archived."}), 200) if r.ok else _failed(r)


@bp.get("/moderators")
@page_required("admin")
def moderators():
    return jsonify({"moderators": [{"id": a.id, "email": a.email, "displayName": a.display_name} for a in _svc().moderators()]})


@bp.post("/moderators")
@page_required("admin")
def set_moderator():
    d = _body()
    r = _svc().set_moderator(g.account.id, d.get("email"), bool(d.get("enable", True)))
    return (jsonify({"message": "Role updated."}), 200) if r.ok else _failed(r)


@bp.get("/settings")
@page_required("admin")
def settings():
    return jsonify({"settings": _svc().list_settings()})


@bp.put("/settings/<name>")
@page_required("admin")
def update_setting(name):
    r = _svc().update_setting(g.account.id, name, _body().get("value"))
    return (jsonify({"settings": r.item}), 200) if r.ok else _failed(r)


@bp.post("/clean-up")
@page_required("admin")
def clean_up():
    """Runs the retention clean-up now (OR-001, OR-002). The same run is available as `flask --app app clean-up`."""
    result = get_service("retention").run(g.account.id)
    return jsonify({"cleanUp": result.as_dict(),
                    "message": f"Clean-up finished: {result.messages_deleted} messages, {result.reports_deleted} closed "
                               f"reports and {result.audit_entries_deleted} audit entries removed."})


@bp.get("/pilot-report")
@page_required("admin")
def pilot_report():
    data = get_service("pilot").report()
    return jsonify({"groups": [dataclasses.asdict(x) for x in data["groups"]], "weekly": data["weekly"],
                    "pilotWeek": data["pilotWeek"],
                    "period": data["period"], "records": data["records"]})


@bp.get("/pilot-report.csv")
@page_required("admin")
def pilot_report_csv():
    return Response(get_service("pilot").report_csv(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=pilot-report.csv"})
