"""Wires services to repositories for one request. Controllers call get_services() only."""
from types import SimpleNamespace

from flask import current_app, g

from .db import connect, init_db
from .repositories import (
    SqliteAccountRepository, SqliteConnectionRepository, SqliteNotificationRepository,
    SqliteProfileRepository, SqliteVerificationTokenRepository,
)
from .services.auth_service import AuthService
from .settings import SettingsProvider


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_database(app):
    conn = connect(app.config["DATABASE_PATH"])
    init_db(conn)
    conn.close()


def get_services():
    if "services" not in g:
        db = get_db()
        settings = SettingsProvider(db)
        accounts = SqliteAccountRepository(db)
        tokens = SqliteVerificationTokenRepository(db)
        gateway = current_app.extensions["email_gateway"]
        clock = current_app.config.get("CLOCK")
        kwargs = {"clock": clock} if clock else {}
        kwargs["hash_method"] = current_app.config["PASSWORD_HASH_METHOD"]
        g.services = SimpleNamespace(
            db=db, settings=settings, accounts=accounts, tokens=tokens,
            profiles=SqliteProfileRepository(db),
            connections=SqliteConnectionRepository(db),
            notifications=SqliteNotificationRepository(db),
            gateway=gateway,
            auth=AuthService(accounts, tokens, settings, gateway, current_app.config["BASE_URL"], **kwargs),
        )
    return g.services
