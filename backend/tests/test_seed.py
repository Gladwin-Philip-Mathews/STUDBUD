import seed_demo
from app import create_app


def test_demo_seed_builds_a_usable_database_and_is_safe_to_repeat(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "demo.db"))
    seed_demo.main()
    seed_demo.main()  # second run changes nothing
    assert "already there" in capsys.readouterr().out
    client = create_app({"TESTING": True}).test_client()
    assert client.post("/api/auth/sign-in", json={"email": "admin@g.rit.edu", "password": seed_demo.PASSWORD}).status_code == 200
    assert client.get("/api/admin/status").get_json()["status"]["accounts"] == 7
