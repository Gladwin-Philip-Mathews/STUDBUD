import sqlite3

from flask import Blueprint, g, jsonify

from app.container import get_service, service
from app.models.enums import Role
from app.security import login_required, role_required

from .test_auth_api import GOOD, register, sign_in, token_from, verified_account


def test_every_schema_file_loads_and_core_tables_exist(app):
    c = sqlite3.connect(app.config["DATABASE_PATH"])
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    c.close()
    assert {"accounts", "profiles", "connections", "notifications", "settings"} <= names


def test_blueprints_are_registered_automatically(app):
    assert {"auth", "health"} <= set(app.blueprints)


def test_a_feature_can_register_its_own_service_and_routes(app, client, gateway):
    @service("demo")
    def build(d):
        return {"n": 1}

    bp = Blueprint("demo_feature", __name__)

    @bp.get("/api/demo/me")
    @login_required
    def me():
        return jsonify({"who": g.account.display_name, "n": get_service("demo")["n"]})

    @bp.get("/api/demo/admin")
    @role_required(Role.ADMINISTRATOR)
    def admin():
        return jsonify({"ok": True})

    app.register_blueprint(bp)
    assert client.get("/api/demo/me").status_code == 401
    verified_account(client, gateway)
    sign_in(client)
    assert client.get("/api/demo/me").get_json() == {"who": "Ana Lee", "n": 1}
    assert client.get("/api/demo/admin").status_code == 403


# ---- M3 conformance: names and behaviour from CD-1a and SD-1 ----
def test_settings_duration_returns_a_time_span(app):
    from datetime import timedelta
    from app.models.enums import SettingName
    from app.settings import SettingsProvider
    from app.container import get_db
    with app.app_context():
        s = SettingsProvider(get_db())
        assert s.duration(SettingName.REQUEST_DECLINE_WAIT) == timedelta(days=30)
        assert s.duration(SettingName.OVERDUE_FLAG) == timedelta(hours=36)
        assert s.value(SettingName.RESEND_LIMIT) == 3


def test_audit_log_appends_and_has_no_edit(app):
    from app.services.audit_log import AuditLog
    from app.container import get_db
    with app.app_context():
        log = AuditLog(get_db())
        log.record(None, "MESSAGE_READ", "message 4", "by moderator")
        assert [e["action"] for e in log.entries()] == ["MESSAGE_READ"]
        assert not hasattr(log, "update") and not hasattr(log, "delete")
