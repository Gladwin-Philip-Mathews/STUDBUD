"""Decorators every controller uses. The backend decides who is signed in and what they may reach (NFR-013).

    @bp.get("/api/profile")
    @login_required
    def my_profile():
        account = g.account          # the signed-in, verified, unsuspended account

    @bp.get("/api/moderation/queue")
    @page_required("moderation")     # CD-1b AuthService.mayAccess(account, ("page", "moderation")); IF-004
    def queue(): ...

    @bp.get("/api/notifications/<int:notification_id>")
    @login_required
    def one(notification_id):
        if not may_access(ItemRef("notification", notification_id)): ...
"""
from functools import wraps

from flask import g, jsonify, session

from .container import get_service
from .models.entities import ItemRef
from .models.enums import Role

NO_ACCESS = "You do not have access to this."


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        account = get_service("auth").current_account(session)  # SD-1 M2, M3
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


def may_access(item: ItemRef) -> bool:
    """The server-side check of CD-1b AuthService.mayAccess() for the signed-in account (NFR-013)."""
    return get_service("auth").may_access(g.get("account"), item)


def page_required(page: str):
    """IF-004: the moderation pages need the Moderator role, the administration pages the System Administrator role."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not may_access(ItemRef("page", page)):
                return jsonify({"message": NO_ACCESS}), 403
            return view(*args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles: Role):
    """Kept for routes that name roles directly; the staff pages use page_required."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(*args, **kwargs):
            if g.account.role not in roles:
                return jsonify({"message": NO_ACCESS}), 403
            return view(*args, **kwargs)
        return wrapper
    return decorator
