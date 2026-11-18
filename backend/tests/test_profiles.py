import pytest

from app.db import connect
from app.models import Course
from app.repositories import SqliteCourseRepository

from .helpers import PASSWORD, make_student, signed_in_client


@pytest.fixture
def courses(app):
    conn = connect(app.config["DATABASE_PATH"])
    repo = SqliteCourseRepository(conn)
    for code, name, status in [("SWEN-261", "Intro to Software Engineering", "active"),
                               ("CSEC-101", "Cybersecurity Basics", "active"),
                               ("MATH-181", "Calculus I", "archived")]:
        repo.add(Course(code, name, status))
    conn.close()


@pytest.fixture
def new_student(app):
    make_student(app, "Newt", with_profile=False)
    return signed_in_client(app, "Newt")


GOOD = {"intent": "both", "cohort": "first year", "yearOfStudy": 1, "interests": ["chess"], "courses": []}


def test_features_are_closed_until_the_profile_exists(new_student):  # FR-010
    assert new_student.get("/api/auth/me").get_json()["profileComplete"] is False
    r = new_student.get("/api/connections/incoming")
    assert r.status_code == 403 and r.get_json()["needsProfile"] is True
    assert new_student.put("/api/profile", json=GOOD).status_code == 200
    assert new_student.get("/api/connections/incoming").status_code == 200


def test_missing_intent_or_cohort_is_named(new_student):  # AC-FR-010a
    r = new_student.put("/api/profile", json={**GOOD, "intent": None})
    assert r.status_code == 400 and "intent" in r.get_json()["errors"]
    r = new_student.put("/api/profile", json={**GOOD, "cohort": ""})
    assert "cohort" in r.get_json()["errors"]
    assert new_student.get("/api/profile").get_json()["profile"] is None


def test_only_courses_on_the_active_list_can_be_added(new_student, courses):  # AC-FR-011a
    ok = new_student.put("/api/profile", json={**GOOD, "courses": ["SWEN-261"]})
    assert ok.status_code == 200 and ok.get_json()["profile"]["courses"] == ["SWEN-261"]
    for bad in (["NOPE-000"], ["MATH-181"]):  # not on the list, and archived
        r = new_student.put("/api/profile", json={**GOOD, "courses": bad})
        assert r.status_code == 400 and "courses" in r.get_json()["errors"]
    assert new_student.put("/api/profile", json={**GOOD, "courses": []}).status_code == 200  # none is fine


def test_course_search_lists_active_courses_only(new_student, courses):
    names = [c["code"] for c in new_student.get("/api/profile/courses?q=s").get_json()["courses"]]
    assert "SWEN-261" in names and "CSEC-101" in names and "MATH-181" not in names


def test_interest_limits(new_student):  # AC-FR-012a
    twenty = [f"i{n}" for n in range(20)]
    assert new_student.put("/api/profile", json={**GOOD, "interests": twenty}).status_code == 200
    assert new_student.put("/api/profile", json={**GOOD, "interests": twenty + ["extra"]}).status_code == 400
    assert new_student.put("/api/profile", json={**GOOD, "interests": ["x" * 31]}).status_code == 400
    assert new_student.put("/api/profile", json={**GOOD, "interests": ["x" * 30]}).status_code == 200


def test_edits_show_up_in_suggestions(app, courses):  # FR-013 (AC-FR-013a)
    make_student(app, "Ann")
    make_student(app, "Bo")
    ann, bo = signed_in_client(app, "Ann"), signed_in_client(app, "Bo")
    bo.put("/api/profile", json={**GOOD, "courses": ["SWEN-261"]})
    ann.put("/api/profile", json={**GOOD, "courses": ["SWEN-261"]})
    names = [s["displayName"] for s in ann.get("/api/connections/suggestions").get_json()["suggestions"]]
    assert "Bo" in names


def test_others_see_only_four_items(app):  # AC-FR-014a
    a = make_student(app, "Ava")
    make_student(app, "Bea")
    ava, bea = signed_in_client(app, "Ava"), signed_in_client(app, "Bea")
    ava.put("/api/profile", json={**GOOD, "yearOfStudy": 3, "cohort": "international", "interests": ["jazz"]})
    seen = bea.get(f"/api/profile/students/{a}").get_json()["student"]
    assert set(seen) == {"id", "displayName", "interests", "courses", "intent"}
    text = str(seen)
    assert "ava@g.rit.edu" not in text and "international" not in text


def test_deleting_the_account_removes_the_personal_data(app):  # AC-FR-015a
    a, b = make_student(app, "Dee"), make_student(app, "Eli")
    dee, eli = signed_in_client(app, "Dee"), signed_in_client(app, "Eli")
    dee.post("/api/connections/requests", json={"receiverId": b})
    assert dee.delete("/api/profile", json={"password": "wrong"}).status_code == 400
    assert dee.delete("/api/profile", json={"password": PASSWORD}).status_code == 200
    login = app.test_client().post("/api/auth/sign-in", json={"email": "dee@g.rit.edu", "password": PASSWORD})
    assert login.status_code != 200
    assert eli.get("/api/connections/incoming").get_json()["requests"] == []
    assert eli.get(f"/api/profile/students/{a}").status_code == 404
    conn = connect(app.config["DATABASE_PATH"])
    row = conn.execute("SELECT status, password_hash, email FROM accounts WHERE id=?", (a,)).fetchone()
    assert row["status"] == "deleted" and row["password_hash"] == "" and "dee@" not in row["email"]
    assert conn.execute("SELECT COUNT(*) c FROM notifications WHERE recipient_id=?", (a,)).fetchone()["c"] == 0
    conn.close()
