import importlib
import os
import pkgutil

import click
from flask import Flask, g, jsonify, redirect, request
from werkzeug.exceptions import HTTPException

from .container import close_db, get_service, init_database
from .email_gateway import build_gateway

# Keys that are fine for a laptop and never for the pilot server (NFR-009, IF-006).
PLACEHOLDER_SECRET_KEYS = {"dev", "change-me", ""}

# NFR-008, NFR-021: a failed request shows a plain message that names the next step, never a stack trace or a
# framework page. Everything under /api is JSON, so the handlers answer in JSON.
PLAIN_MESSAGES = {
    404: "That page or item was not found. Check the address or go back to the feed.",
    405: "That action is not available here. Go back and try again from the page.",
    413: "That is too large to send. Shorten it and try again.",
    429: "Too many attempts in a short time. Wait a few minutes and try again.",
    500: "Something went wrong on our side and nothing was saved. Try again in a moment; if it keeps happening, "
         "tell the StudBud team.",
}


def create_app(config=None):
    """Application factory. Controllers are registered here as they are built."""
    app = Flask(__name__)
    force_https = os.getenv("FORCE_HTTPS", "0").lower() in ("1", "true", "yes")
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "studbud.db"),
        EMAIL_MODE=os.getenv("EMAIL_MODE", "stub"),
        SMTP_HOST=os.getenv("SMTP_HOST", ""),
        SMTP_PORT=os.getenv("SMTP_PORT", "587"),
        SMTP_SENDER=os.getenv("SMTP_SENDER", ""),
        SMTP_USER=os.getenv("SMTP_USER", ""),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        BASE_URL=os.getenv("BASE_URL", "http://localhost:4200"),
        # IF-006, NFR-010: on the pilot server FORCE_HTTPS=1 redirects plain HTTP, marks the session cookie Secure and
        # sends HSTS. Off by default so the laptop setup (http://localhost) keeps working.
        FORCE_HTTPS=force_https,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,  # the browser script never needs the session cookie (NFR-013)
        SESSION_COOKIE_SECURE=force_https,
        PREFERRED_URL_SCHEME="https" if force_https else "http",
        PASSWORD_HASH_METHOD="pbkdf2:sha256",
        EMAIL_DISPATCH="after_response",  # "manual" lets tests control when emails go out
    )
    if config:
        app.config.update(config)
        if "FORCE_HTTPS" in config:  # the test or deployment config decides; keep the dependent settings in step
            app.config.setdefault("SESSION_COOKIE_SECURE", None)
            if config.get("SESSION_COOKIE_SECURE") is None:
                app.config["SESSION_COOKIE_SECURE"] = bool(config["FORCE_HTTPS"])
            app.config["PREFERRED_URL_SCHEME"] = "https" if config["FORCE_HTTPS"] else "http"
    if app.config["FORCE_HTTPS"] and app.config["SECRET_KEY"] in PLACEHOLDER_SECRET_KEYS:
        # A guessable key lets anyone forge a session cookie, so the server refuses to start with one (NFR-009).
        raise RuntimeError("SECRET_KEY must be set to a long random value when FORCE_HTTPS is on.")

    # DD-03: one email route. Live gateway is added last (CON-009); the stub is used until then.
    # In development the stub prints each email (including verification links) in the backend window.
    app.extensions["email_gateway"] = build_gateway(app.config, echo=not app.config.get("TESTING"))
    init_database(app)
    app.teardown_appcontext(close_db)

    @app.before_request
    def refuse_plain_http():
        """IF-006: a request on the plain HTTP address is redirected to HTTPS and no content is returned over HTTP."""
        if not app.config["FORCE_HTTPS"]:
            return None
        forwarded = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
        if request.is_secure or forwarded == "https":
            return None
        if request.method in ("GET", "HEAD"):
            return redirect(request.url.replace("http://", "https://", 1), code=308)
        return jsonify({"message": "Use the secure address (https) for StudBud."}), 403

    @app.after_request
    def security_headers(response):
        if app.config["FORCE_HTTPS"]:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")  # CON-002: no address leaks to third parties
        return response

    @app.after_request
    def hand_over_emails_after_response(response):
        if g.pop("email_pending", False) and app.config["EMAIL_DISPATCH"] == "after_response":
            from .email_dispatch import dispatch_pending_emails
            response.call_on_close(lambda: dispatch_pending_emails(app))
        return response

    @app.errorhandler(HTTPException)
    def plain_http_error(error):
        if error.code in PLAIN_MESSAGES:
            return jsonify({"message": PLAIN_MESSAGES[error.code]}), error.code
        return jsonify({"message": error.description}), error.code

    if not app.config.get("TESTING") or app.config.get("PLAIN_ERRORS"):
        # In tests an unexpected error should surface as a traceback; set PLAIN_ERRORS to test the handler itself.
        @app.errorhandler(Exception)
        def plain_server_error(error):
            # NFR-008: the request's database work is rolled back when the connection closes without a commit, so
            # nothing half-saved remains; the student sees a plain message and can repeat the action.
            app.logger.exception("Unhandled error: %s", error)
            return jsonify({"message": PLAIN_MESSAGES[500]}), 500

    # Every module in controllers/ that defines `bp` (a Blueprint) is registered automatically.
    from . import controllers
    for module in pkgutil.iter_modules(controllers.__path__):
        blueprint = getattr(importlib.import_module(f"{controllers.__name__}.{module.name}"), "bp", None)
        if blueprint is not None:
            app.register_blueprint(blueprint)

    @app.cli.command("clean-up")
    def clean_up_command():
        """Apply the retention rules (OR-001, OR-002). Schedule this daily on the pilot server."""
        result = get_service("retention").run(None)
        click.echo(f"Clean-up finished: {result.messages_deleted} messages, {result.reports_deleted} closed reports, "
                   f"{result.audit_entries_deleted} audit entries removed.")

    return app
