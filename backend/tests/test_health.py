from app import create_app


def test_health_endpoint_returns_ok(tmp_path):
    client = create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "health.db")}).test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
