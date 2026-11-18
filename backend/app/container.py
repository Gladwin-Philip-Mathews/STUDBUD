"""Wiring. Each feature registers its own service factory in its own file, so no shared file needs editing.

In a service module:

    @service("profiles")
    def build(d):                      # d = Deps (db, settings, repositories, gateway, clock, config)
        return ProfileService(d.profiles, d.settings)

In a controller:

    svc = get_service("profiles")
"""
import importlib
import pkgutil
from types import SimpleNamespace

from flask import current_app, g

from .db import connect, init_db
from .repositories import (
    SqliteAccountRepository, SqliteConnectionRepository, SqliteCourseRepository, SqliteNotificationRepository,
    SqliteProfileRepository, SqliteVerificationTokenRepository,
    SqliteCommunityRepository, SqlitePostRepository,
)
from .settings import SettingsProvider

_factories = {}
_services_imported = False


def service(name):
    """Register a factory that builds a service from the request's Deps."""
    def register(factory):
        _factories[name] = factory
        return factory
    return register


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


def _import_all(package_name):
    package = importlib.import_module(package_name)
    for mod in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"{package_name}.{mod.name}")


def _flag_email_pending():
    """Ask for the email to be handed over after the response is sent (DD-04)."""
    g.email_pending = True


def get_deps():
    if "deps" not in g:
        db = get_db()
        g.deps = SimpleNamespace(
            db=db,
            settings=SettingsProvider(db),
            accounts=SqliteAccountRepository(db),
            tokens=SqliteVerificationTokenRepository(db),
            profiles=SqliteProfileRepository(db),
            connections=SqliteConnectionRepository(db),
            courses=SqliteCourseRepository(db),
            communities=SqliteCommunityRepository(db),
            posts=SqlitePostRepository(db),
            notifications=SqliteNotificationRepository(db),
            gateway=current_app.extensions["email_gateway"],
            on_email_pending=_flag_email_pending,
            clock=current_app.config.get("CLOCK"),
            config=current_app.config,
            services={},
        )
    return g.deps


def get_service(name):
    global _services_imported
    deps = get_deps()
    if name not in deps.services:
        if not _services_imported:
            _import_all(f"{__package__}.services")
            _services_imported = True
        deps.services[name] = _factories[name](deps)
    return deps.services[name]
