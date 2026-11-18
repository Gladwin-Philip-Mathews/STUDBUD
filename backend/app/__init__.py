import importlib
import os
import pkgutil

from flask import Flask, g

from .container import close_db, init_database
from .email_gateway import build_gateway


def create_app(config=None):
    """Application factory. Controllers are registered here as they are built."""
    app = Flask(__name__)
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
        SESSION_COOKIE_SAMESITE="Lax",
        PASSWORD_HASH_METHOD="pbkdf2:sha256",
        EMAIL_DISPATCH="after_response",  # "manual" lets tests control when emails go out
    )
    if config:
        app.config.update(config)

    # DD-03: one email route. Live gateway is added last (CON-009); the stub is used until then.
    # In development the stub prints each email (including verification links) in the backend window.
    app.extensions["email_gateway"] = build_gateway(app.config, echo=not app.config.get("TESTING"))
    init_database(app)
    app.teardown_appcontext(close_db)

    @app.after_request
    def hand_over_emails_after_response(response):
        if g.pop("email_pending", False) and app.config["EMAIL_DISPATCH"] == "after_response":
            from .email_dispatch import dispatch_pending_emails
            response.call_on_close(lambda: dispatch_pending_emails(app))
        return response

    # Every module in controllers/ that defines `bp` (a Blueprint) is registered automatically.
    from . import controllers
    for module in pkgutil.iter_modules(controllers.__path__):
        blueprint = getattr(importlib.import_module(f"{controllers.__name__}.{module.name}"), "bp", None)
        if blueprint is not None:
            app.register_blueprint(blueprint)

    return app
