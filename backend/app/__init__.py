from flask import Flask


def create_app(config=None):
    """Application factory. Controllers are registered here as they are built."""
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY="dev", DATABASE_PATH="studbud.db")
    if config:
        app.config.update(config)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
