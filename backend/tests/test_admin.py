import pytest

from app.container import get_service
from app.db import connect
from app.models import Profile

from .helpers import PASSWORD, make_student, signed_in_client

GOOD = {"intent": "both", "cohort": "first year", "interests": [], "courses": []}


def sql(app, query, *args):
    conn = connect(app.config["DATABASE_PATH"])
    conn.execute(query, args)
    conn.commit()
    conn.close()


@pytest.fixture
def people(app):
    ids = {n: make_student(app, n) for n in ("Root", "Stu", "Mo")}
    sql(app, "UPDATE accounts SET role='administrator' WHERE id=?", ids["Root"])
    return ids, {n: signed_in_client(app, n) for n in ids}


def test_only_administrators_reach_admin_endpoints(people):  # NFR-013
    ids, cl = people
    assert cl["Stu"].get("/api/admin/courses").status_code == 403
    assert cl["Stu"].post("/api/admin/courses", json={"code": "X-1", "title": "T"}).status_code == 403
    assert cl["Root"].get("/api/admin/courses").status_code == 200


def test_adding_a_course_makes_its_community_and_rejects_duplicates(people):  # FR-100, FR-020
    ids, cl = people
    assert cl["Root"].post("/api/admin/courses", json={"code": "swen-261", "title": "Software Engineering"}).status_code == 201
    r = cl["Root"].post("/api/admin/courses", json={"code": "SWEN-261", "title": "Again"})
    assert r.status_code == 400 and "code" in r.get_json()["errors"]
    assert any(c["code"] == "SWEN-261" for c in cl["Root"].get("/api/admin/courses").get_json()["courses"])
    cl["Stu"].put("/api/profile", json={**GOOD, "courses": ["SWEN-261"]})
    names = [c["name"] for c in cl["Stu"].get("/api/communities").get_json()["communities"]]
    assert any(n.startswith("SWEN-261") for n in names)


def test_rename_a_course(people):  # FR-100
    ids, cl = people
    cl["Root"].post("/api/admin/courses", json={"code": "CSEC-101", "title": "Old"})
    assert cl["Root"].put("/api/admin/courses/CSEC-101", json={"title": "New title"}).get_json()["course"]["title"] == "New title"
    assert cl["Root"].put("/api/admin/courses/NOPE-1", json={"title": "x"}).status_code == 404


def test_import_adds_valid_rows_and_lists_duplicates(people):  # AC-FR-100a
    ids, cl = people
    rows = [f"COUR-{n:03d},Course number {n}" for n in range(28)]
    rows += ["COUR-001,Duplicate one", "COUR-002,Duplicate two"]
    r = cl["Root"].post("/api/admin/courses/import", json={"csv": "code,title\n" + "\n".join(rows)}).get_json()
    assert len(r["added"]) == 28 and r["duplicates"] == ["COUR-001", "COUR-002"]
    assert "COUR-001" in r["message"] and "COUR-002" in r["message"]


def test_archived_course_cannot_be_added_but_existing_students_keep_it(people):  # AC-FR-100b, FR-025
    ids, cl = people
    cl["Root"].post("/api/admin/courses", json={"code": "OLD-100", "title": "Old course"})
    cl["Stu"].put("/api/profile", json={**GOOD, "courses": ["OLD-100"]})
    assert cl["Root"].post("/api/admin/courses/OLD-100/archive").status_code == 200
    cl["Mo"].put("/api/profile", json=GOOD)
    assert cl["Mo"].put("/api/profile", json={**GOOD, "courses": ["OLD-100"]}).status_code == 400
    kept = cl["Stu"].put("/api/profile", json={**GOOD, "interests": ["chess"], "courses": ["OLD-100"]})
    assert kept.status_code == 200 and kept.get_json()["profile"]["courses"] == ["OLD-100"]


def test_removing_a_domain_takes_effect_without_a_restart(people, client):  # AC-FR-101a
    ids, cl = people
    body = {"email": "new@g.rit.edu", "displayName": "Newcomer", "password": "passw0rdX", "acceptNotice": True}
    assert cl["Root"].delete("/api/admin/domains/g.rit.edu").status_code == 200
    assert client.post("/api/auth/register", json=body).status_code == 400
    assert cl["Root"].post("/api/admin/domains", json={"domain": "g.rit.edu"}).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 202
    listed = cl["Root"].get("/api/admin/domains").get_json()["domains"]
    assert any(d["domain"] == "g.rit.edu" and d["addedAt"] for d in listed)  # DR-013
    assert cl["Root"].post("/api/admin/domains", json={"domain": "not a domain"}).status_code == 400


def test_assigning_and_removing_the_moderator_role_is_audited(people, app):  # AC-FR-102a
    ids, cl = people
    assert cl["Mo"].get("/api/moderation/queue").status_code == 403
    assert cl["Root"].post("/api/admin/moderators", json={"email": "mo@g.rit.edu", "enable": True}).status_code == 200
    assert cl["Mo"].get("/api/moderation/queue").status_code == 200
    assert cl["Root"].get("/api/admin/moderators").get_json()["moderators"][0]["email"] == "mo@g.rit.edu"
    assert cl["Root"].post("/api/admin/moderators", json={"email": "mo@g.rit.edu", "enable": False}).status_code == 200
    assert cl["Mo"].get("/api/moderation/queue").status_code == 403
    with app.app_context():
        actions = [e["action"] for e in get_service("audit").entries()]
    assert "ROLE_ASSIGNED" in actions and "ROLE_REMOVED" in actions
    assert cl["Root"].post("/api/admin/moderators", json={"email": "nobody@g.rit.edu"}).status_code == 400


def test_interest_communities_can_be_created_renamed_and_archived(people):  # FR-102
    ids, cl = people
    cid = cl["Root"].post("/api/admin/communities", json={"name": "Chess club"}).get_json()["community"]["id"]
    assert cl["Root"].post("/api/admin/communities", json={"name": "chess club"}).status_code == 400
    assert cl["Root"].put(f"/api/admin/communities/{cid}", json={"name": "Chess and Go"}).status_code == 200
    assert cl["Root"].post(f"/api/admin/communities/{cid}/archive").status_code == 200
    assert cl["Stu"].post(f"/api/communities/{cid}/join").status_code == 400  # archived: not joinable


def test_changing_a_setting_applies_on_the_next_view(people, app, clock):  # AC-FR-104a
    from app.models import SafetyReport
    ids, cl = people
    sql(app, "UPDATE accounts SET role='moderator' WHERE id=?", ids["Mo"])
    sql(app, "INSERT INTO safety_reports(reporter_id, reported_student_id, item_type, item_id, reason, text, received_at) "
             "VALUES (?,?,?,?,?,?,?)", ids["Stu"], ids["Root"], "student", ids["Root"], "spam", "",
        (clock() - __import__("datetime").timedelta(hours=30)).isoformat())
    assert cl["Mo"].get("/api/moderation/queue").get_json()["reports"][0]["overdue"] is False  # 30h < 36h
    assert cl["Root"].put("/api/admin/settings/OVERDUE_FLAG", json={"value": 24}).status_code == 200
    assert cl["Mo"].get("/api/moderation/queue").get_json()["reports"][0]["overdue"] is True


def test_settings_reject_unknown_names_and_bad_values(people):  # DR-014
    ids, cl = people
    assert cl["Root"].put("/api/admin/settings/NOT_A_SETTING", json={"value": 5}).status_code == 400
    assert cl["Root"].put("/api/admin/settings/RESEND_LIMIT", json={"value": 0}).status_code == 400
    assert cl["Root"].put("/api/admin/settings/RESEND_LIMIT", json={"value": "x"}).status_code == 400
    listed = {s["name"]: s["value"] for s in cl["Root"].get("/api/admin/settings").get_json()["settings"]}
    assert listed["OVERDUE_FLAG"] == 36 and "MESSAGE_RETENTION" in listed


def test_system_status_counts_match_the_data(people, app, clock):  # AC-FR-103a
    ids, cl = people
    cl["Stu"].put("/api/profile", json=GOOD)
    cl["Root"].post("/api/admin/courses", json={"code": "ST-100", "title": "Status"})
    cl["Stu"].put("/api/profile", json={**GOOD, "courses": ["ST-100"]})
    community = next(c for c in cl["Stu"].get("/api/communities").get_json()["communities"] if c["kind"] == "course")["id"]
    cl["Stu"].post(f"/api/communities/{community}/posts", json={"kind": "share", "title": "A fine post", "text": "text"})
    sql(app, "INSERT INTO safety_reports(reporter_id, reported_student_id, item_type, item_id, reason, text, received_at) "
             "VALUES (?,?,?,?,?,?,?)", ids["Stu"], ids["Mo"], "student", ids["Mo"], "spam", "", clock().isoformat())
    sql(app, "INSERT INTO notifications(recipient_id, event_type, body, created_at, email_status) VALUES (?,?,?,?,?)",
        ids["Stu"], "REPLY_ADDED", "x", clock().isoformat(), "returned")
    status = cl["Root"].get("/api/admin/status").get_json()["status"]
    assert status["accounts"] == 3 and status["posts"] == 1 and status["openReports"] == 1 and status["failedEmails"] == 1
    assert status["activeUsers"] >= 0


def test_a_student_suggests_an_interest_and_the_administrator_decides(people):  # FR-102
    ids, cl = people
    r = cl["Stu"].post("/api/communities/suggestions", json={"name": "Movies"})
    assert r.status_code == 201
    assert cl["Stu"].post("/api/communities/suggestions", json={"name": "movies"}).status_code == 400  # already suggested
    assert cl["Stu"].post("/api/communities/suggestions", json={"name": "ab"}).status_code == 400  # too short
    assert cl["Stu"].get("/api/admin/interest-suggestions").status_code == 403  # students cannot read the list
    listed = cl["Root"].get("/api/admin/interest-suggestions").get_json()["suggestions"]
    assert [s["name"] for s in listed] == ["Movies"] and listed[0]["suggestedByName"] == "Stu"
    made = cl["Root"].post(f"/api/admin/interest-suggestions/{listed[0]['id']}/create")
    assert made.status_code == 201
    names = [c["name"] for c in cl["Stu"].get("/api/communities").get_json()["communities"]]
    assert "Movies" in names
    assert cl["Root"].get("/api/admin/interest-suggestions").get_json()["suggestions"] == []
    assert cl["Stu"].post("/api/communities/suggestions", json={"name": "Movies"}).status_code == 400  # exists now


def test_suggestions_can_be_dismissed_and_are_limited(people):
    ids, cl = people
    for n in range(5):
        assert cl["Stu"].post("/api/communities/suggestions", json={"name": f"Topic {n}x"}).status_code == 201
    assert cl["Stu"].post("/api/communities/suggestions", json={"name": "One more"}).status_code == 400
    first = cl["Root"].get("/api/admin/interest-suggestions").get_json()["suggestions"][0]["id"]
    assert cl["Root"].post(f"/api/admin/interest-suggestions/{first}/dismiss").status_code == 200
    assert cl["Root"].post(f"/api/admin/interest-suggestions/{first}/dismiss").status_code == 404
    assert cl["Stu"].post("/api/communities/suggestions", json={"name": "One more"}).status_code == 201
