"""Decorators every controller uses. The backend decides who is signed in (NFR-013).

    @bp.get("/api/profile")
    @login_required
    def my_profile():
        account = g.account          # the signed-in, verified, unsuspended account

    @bp.get("/api/moderation/queue")
    @role_required(Role.MODERATOR, Role.ADMINISTRATOR)
    def queue(): ...
"""
from functools import wraps

from flask import g, jsonify, session

from .container import get_service
from .models.enums import Role


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        account = get_service("auth").current_account(session)
        if account is None:
            return jsonify({"message": "Not signed in."}), 401
        g.account = account
        return view(*args, **kwargs)
    return wrapper


def profile_required(view):
    """FR-010: until intent and cohort are saved, other features are not available."""
    @login_required
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not get_service("profiles").is_complete(g.account.id):
            return jsonify({"message": "Complete your profile first.", "needsProfile": True}), 403
        return view(*args, **kwargs)
    return wrapper


def role_required(*roles: Role):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(*args, **kwargs):
            if g.account.role not in roles:
                return jsonify({"message": "You do not have access to this."}), 403
            return view(*args, **kwargs)
        return wrapper
    return decorator
