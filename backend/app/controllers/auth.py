"""Auth endpoints. No business rule lives here (DD-10): each route calls one AuthService operation."""
from flask import Blueprint, jsonify, request, session

from ..container import get_service
from ..services.auth_service import ResendOutcome, SignInOutcome

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# One message for a new and an existing address (FR-004), so registration reveals nothing.
REGISTERED_MESSAGE = ("If this address can be registered, we have sent a verification message. "
                      "If you already have an account, sign in or ask for a new verification message.")
SIGN_IN_FAILED = "Email or password is incorrect."


def account_json(a):
    return {"id": a.id, "email": a.email, "displayName": a.display_name, "role": a.role.value}


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    result = get_service("auth").register(data.get("email"), data.get("displayName"), data.get("password"))
    if not result.ok:
        return jsonify({"errors": result.field_errors}), 400
    return jsonify({"message": REGISTERED_MESSAGE}), 202


@bp.post("/verify")
def verify():
    data = request.get_json(silent=True) or {}
    account = get_service("auth").verify(data.get("token"))
    if account is None:
        return jsonify({"message": "This link is invalid or has expired. You can ask for a new one.",
                        "canResend": True}), 400
    return jsonify({"message": "Your account is verified.", "next": "/profile"}), 200


@bp.post("/resend")
def resend():
    data = request.get_json(silent=True) or {}
    outcome = get_service("auth").resend_verification(data.get("email"))
    if outcome == ResendOutcome.LIMIT:
        return jsonify({"message": "Too many requests. Try again in an hour."}), 429
    return jsonify({"message": "If that address has an unverified account, we sent a new message."}), 202


@bp.post("/sign-in")
def sign_in():
    data = request.get_json(silent=True) or {}
    auth = get_service("auth")
    result = auth.sign_in(data.get("email"), data.get("password"))
    if result.outcome == SignInOutcome.OK:
        auth.start_session(session, result.account)
        return jsonify({"account": account_json(result.account)}), 200
    if result.outcome == SignInOutcome.UNVERIFIED:
        return jsonify({"message": "Please verify your email first.", "canResend": True}), 403
    if result.outcome == SignInOutcome.LOCKED:
        return jsonify({"message": "Too many failed attempts. Try again later."}), 429
    if result.outcome == SignInOutcome.SUSPENDED:
        return jsonify({"message": "This account is suspended."}), 403
    return jsonify({"message": SIGN_IN_FAILED}), 401


@bp.post("/sign-out")
def sign_out():
    get_service("auth").sign_out(session)
    return jsonify({"message": "Signed out."}), 200


@bp.get("/me")
def me():
    account = get_service("auth").current_account(session)
    if account is None:
        return jsonify({"message": "Not signed in."}), 401
    return jsonify({"account": account_json(account)}), 200
