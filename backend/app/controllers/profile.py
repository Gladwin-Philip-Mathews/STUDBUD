"""Profile endpoints (process 2.0). No rules here: each route calls one ProfileService operation."""
from flask import Blueprint, g, jsonify, request, session

from ..container import get_service
from ..security import login_required

bp = Blueprint("profile", __name__, url_prefix="/api/profile")


def profile_json(p):
    return {"intent": p.intent, "cohort": p.cohort, "yearOfStudy": p.year_of_study,
            "interests": p.interests, "courses": p.course_codes}


@bp.get("")
@login_required
def mine():
    p = get_service("profiles").get(g.account.id)
    return jsonify({"profile": profile_json(p) if p else None})


@bp.put("")
@login_required
def save():
    d = request.get_json(silent=True) or {}
    result = get_service("profiles").save(g.account.id, d.get("intent"), d.get("cohort"), d.get("yearOfStudy"),
                                          d.get("interests"), d.get("courses"))
    if not result.ok:
        return jsonify({"errors": result.errors}), 400
    return jsonify({"profile": profile_json(result.profile)}), 200


@bp.get("/courses")
@login_required
def courses():
    found = get_service("profiles").search_courses(request.args.get("q", ""))
    return jsonify({"courses": [{"code": c.code, "name": c.name} for c in found]})


@bp.get("/students/<int:student_id>")
@login_required
def view(student_id):
    v = get_service("profiles").public_view(student_id)
    if v is None:
        return jsonify({"message": "This student is not available."}), 404
    return jsonify({"student": v})


@bp.delete("")
@login_required
def delete_account():
    d = request.get_json(silent=True) or {}
    if not get_service("profiles").delete_account(g.account.id, d.get("password")):
        return jsonify({"message": "The password is not correct."}), 400
    get_service("auth").sign_out(session)
    return jsonify({"message": "Your account has been deleted."}), 200
