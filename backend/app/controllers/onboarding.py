"""Onboarding question endpoints (process 8.0, FR-090)."""
from flask import Blueprint, g, jsonify, request

from ..container import get_service
from ..models.pilot import ANSWERS
from ..security import profile_required

bp = Blueprint("onboarding", __name__, url_prefix="/api/onboarding")
QUESTION = "How many students on campus do you speak with regularly?"


@bp.get("/question")
@profile_required
def question():
    week = get_service("pilot").pending_question(g.account.id)
    if week is None:
        return jsonify({"question": None})
    return jsonify({"question": {"week": week, "text": QUESTION, "choices": [a for a in ANSWERS if a != "skipped"]}})


@bp.post("/answer")
@profile_required
def answer():
    stored = get_service("pilot").answer(g.account.id, (request.get_json(silent=True) or {}).get("answer"))
    if stored is None:
        return jsonify({"message": "There is no question to answer."}), 400
    return jsonify({"message": "Thank you."}), 201
