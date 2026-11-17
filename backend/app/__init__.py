import os

from flask import Flask

from .container import close_db, init_database
from .email_gateway import StubEmailGateway


def create_app(config=None):
    """Application factory. Controllers are registered here as they are built."""
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "studbud.db"),
        EMAIL_MODE=os.getenv("EMAIL_MODE", "stub"),
        BASE_URL=os.getenv("BASE_URL", "http://localhost:4200"),
        SESSION_COOKIE_SAMESITE="Lax",
        PASSWORD_HASH_METHOD="pbkdf2:sha256",
    )
    if config:
        app.config.update(config)

    # DD-03: one email route. Live gateway is added last (CON-009); the stub is used until then.
    app.extensions["email_gateway"] = StubEmailGateway()
    init_database(app)
    app.teardown_appcontext(close_db)

    from .controllers import auth
    app.register_blueprint(auth.bp)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
