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
