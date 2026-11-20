import pytest

from app.db import connect
from app.models import Course
from app.repositories import SqliteCourseRepository

from .helpers import make_student, signed_in_client

GOOD_PROFILE = {"intent": "both", "cohort": "first year", "interests": [], "courses": ["SWEN-261"]}


def db(app):
    return connect(app.config["DATABASE_PATH"])


@pytest.fixture
def world(app):
    """Ann and Bo take SWEN-261; Cy does not. One interest community, made by an administrator."""
    conn = db(app)
    SqliteCourseRepository(conn).add(Course("SWEN-261", "Intro to Software Engineering"))
    conn.close()
    ids = {n: make_student(app, n) for n in ("Ann", "Bo", "Cy", "Root")}
    conn = db(app)
    conn.execute("UPDATE accounts SET role='administrator' WHERE id=?", (ids["Root"],))
    conn.commit()
    conn.close()
    cl = {n: signed_in_client(app, n) for n in ids}
    for n in ("Ann", "Bo"):
        assert cl[n].put("/api/profile", json=GOOD_PROFILE).status_code == 200
    cid = cl["Root"].post("/api/communities", json={"name": "Chess club"}).get_json()["community"]["id"]
    course = next(c for c in cl["Ann"].get("/api/communities").get_json()["communities"] if c["kind"] == "course")
    return {"ids": ids, "c": cl, "interest": cid, "course": course["id"]}


def post(client, cid, **over):
    body = {"kind": "question", "title": "How do I start?", "text": "Where do I begin with the project?", **over}
    return client.post(f"/api/communities/{cid}/posts", json=body)


def test_adding_a_course_puts_the_student_in_its_community(world):  # FR-022, AC-FR-022a
    ann = world["c"]["Ann"].get("/api/communities").get_json()["communities"]
    mine = next(c for c in ann if c["id"] == world["course"])
    assert mine["joined"] is True and mine["memberCount"] == 2 and "collaboration rules" in mine["notice"]  # FR-039
    cy = next(c for c in world["c"]["Cy"].get("/api/communities").get_json()["communities"] if c["id"] == world["course"])
    assert cy["joined"] is False


def test_removing_the_course_takes_the_student_out(world):  # FR-022
    world["c"]["Ann"].put("/api/profile", json={**GOOD_PROFILE, "courses": []})
    ann = world["c"]["Ann"].get("/api/communities").get_json()["communities"]
    assert next(c for c in ann if c["id"] == world["course"])["joined"] is False


def test_joining_rules(world):  # FR-023
    cy = world["c"]["Cy"]
    assert cy.post(f"/api/communities/{world['course']}/join").status_code == 400  # course not on profile
    assert cy.post(f"/api/communities/{world['interest']}/join").status_code == 200
    assert cy.post(f"/api/communities/{world['interest']}/leave").status_code == 200


def test_only_administrators_create_interest_communities(world):  # FR-021
    ann, root = world["c"]["Ann"], world["c"]["Root"]
    assert ann.post("/api/communities", json={"name": "Hiking"}).status_code == 403
    assert root.post("/api/communities", json={"name": "ab"}).status_code == 400
    assert root.post("/api/communities", json={"name": "chess CLUB"}).status_code == 400  # duplicate name


def test_search_communities_by_part_of_the_name(world):  # FR-024
    found = world["c"]["Ann"].get("/api/communities?q=chess").get_json()["communities"]
    assert [c["name"] for c in found] == ["Chess club"]


def test_post_limits_and_named_problems(world):  # FR-030, FR-031
    ann = world["c"]["Ann"]
    assert post(ann, world["course"]).status_code == 201
    r = post(ann, world["course"], kind=None, title="abc", text="")
    assert set(r.get_json()["errors"]) == {"kind", "title", "text"}
    assert post(ann, world["course"], title="x" * 121).status_code == 400
    assert post(ann, world["course"], title="x" * 120, text="y" * 2000).status_code == 201
    assert post(ann, world["course"], text="y" * 2001).status_code == 400


def test_only_members_can_post_or_read(world):
    cy = world["c"]["Cy"]
    assert post(cy, world["course"]).status_code == 404
    pid = post(world["c"]["Ann"], world["course"]).get_json()["post"]["id"]
    assert cy.get(f"/api/posts/{pid}").status_code == 404
    assert cy.get(f"/api/communities/{world['course']}/posts").status_code == 404


def test_reply_notifies_the_author_in_time_order(world):  # FR-032, FR-080
    ann, bo = world["c"]["Ann"], world["c"]["Bo"]
    pid = post(ann, world["course"]).get_json()["post"]["id"]
    assert bo.post(f"/api/posts/{pid}/replies", json={"text": "first"}).status_code == 201
    assert bo.post(f"/api/posts/{pid}/replies", json={"text": "second"}).status_code == 201
    assert bo.post(f"/api/posts/{pid}/replies", json={"text": "x" * 1001}).status_code == 400
    assert [r["text"] for r in ann.get(f"/api/posts/{pid}").get_json()["post"]["replies"]] == ["first", "second"]
    notes = ann.get("/api/notifications").get_json()
    assert notes["unread"] == 2 and "Bo replied" in notes["notifications"][0]["body"]
    ann.post(f"/api/posts/{pid}/replies", json={"text": "thanks"})  # replying to yourself does not notify
    assert ann.get("/api/notifications").get_json()["unread"] == 2


def test_edit_within_15_minutes_then_not(world, clock):  # FR-033
    ann = world["c"]["Ann"]
    pid = post(ann, world["course"]).get_json()["post"]["id"]
    clock.advance(minutes=14)
    r = ann.put(f"/api/posts/{pid}", json={"title": "Better title", "text": "Better text"})
    assert r.status_code == 200 and r.get_json()["post"]["edited"] is True
    clock.advance(minutes=2)
    # the 2 hour idle limit is not reached, so the same session still works
    assert ann.put(f"/api/posts/{pid}", json={"title": "Too late now", "text": "x"}).status_code == 400


def test_author_can_delete_others_cannot(world):  # FR-033
    ann, bo = world["c"]["Ann"], world["c"]["Bo"]
    pid = post(ann, world["course"]).get_json()["post"]["id"]
    assert bo.delete(f"/api/posts/{pid}").status_code == 404
    assert ann.delete(f"/api/posts/{pid}").status_code == 200
    assert bo.get(f"/api/posts/{pid}").status_code == 404


def test_feed_is_newest_first_with_20_per_page_and_kind_filter(world, clock):  # FR-034, FR-037
    ann = world["c"]["Ann"]
    for n in range(21):
        clock.advance(seconds=1)
        post(ann, world["course"], title=f"Post number {n:02d}", kind="share" if n % 2 else "question")
    first = ann.get("/api/feed").get_json()
    assert len(first["posts"]) == 20 and first["hasMore"] is True
    assert first["posts"][0]["title"] == "Post number 20"
    assert len(ann.get("/api/feed?page=2").get_json()["posts"]) == 1
    only = ann.get("/api/feed?kind=share").get_json()["posts"]
    assert only and all(p["kind"] == "share" for p in only)
    assert world["c"]["Cy"].get("/api/feed").get_json()["message"]  # empty message


def test_search_posts(world):  # FR-036
    ann, cy = world["c"]["Ann"], world["c"]["Cy"]
    post(ann, world["course"], title="Sprint planning help", text="How long should a sprint be?")
    assert ann.get("/api/search?q=sprint").get_json()["posts"]
    assert ann.get("/api/search?q=sprint+zzz").get_json()["message"] == "No posts found."
    assert ann.get("/api/search?q=s").status_code == 400
    assert cy.get("/api/search?q=sprint").get_json()["posts"] == []  # not in that community


def test_archived_community_stays_readable_but_refuses_new_content(world, app):  # FR-025
    ann = world["c"]["Ann"]
    pid = post(ann, world["course"]).get_json()["post"]["id"]
    conn = db(app)
    conn.execute("UPDATE communities SET status='archived' WHERE id=?", (world["course"],))
    conn.commit()
    conn.close()
    assert ann.get(f"/api/posts/{pid}").status_code == 200
    assert "community" in post(ann, world["course"]).get_json()["errors"]
    assert "community" in ann.post(f"/api/posts/{pid}/replies", json={"text": "hi"}).get_json()["errors"]


def test_hidden_post_shows_only_to_its_author_with_a_notice(world, app):  # FR-065
    ann, bo = world["c"]["Ann"], world["c"]["Bo"]
    pid = post(ann, world["course"]).get_json()["post"]["id"]
    conn = db(app)
    conn.execute("UPDATE posts SET status='hidden' WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    assert "hidden" in ann.get(f"/api/posts/{pid}").get_json()["post"]["notice"]
    assert bo.get(f"/api/posts/{pid}").status_code == 404
    assert all(p["id"] != pid for p in bo.get("/api/feed").get_json()["posts"])


def test_deleted_student_shows_as_deleted_student(world):  # FR-015
    ann, bo = world["c"]["Ann"], world["c"]["Bo"]
    pid = post(ann, world["course"]).get_json()["post"]["id"]
    from .helpers import PASSWORD
    assert ann.delete("/api/profile", json={"password": PASSWORD}).status_code == 200
    assert bo.get(f"/api/posts/{pid}").get_json()["post"]["author"]["displayName"] == "deleted student"



def test_posts_and_community_page_name_their_community(world):  # the feed, the community page and the post view say where a post is from
    ann = world["c"]["Ann"]
    pid = post(ann, world["course"]).get_json()["post"]["id"]
    assert "SWEN-261" in post(ann, world["course"], title="Another question").get_json()["post"]["community"]
    assert any("SWEN-261" in p["community"] for p in ann.get("/api/feed").get_json()["posts"])
    assert "SWEN-261" in ann.get(f"/api/posts/{pid}").get_json()["post"]["community"]
    page = ann.get(f"/api/communities/{world['course']}/posts").get_json()
    assert "SWEN-261" in page["community"]["name"] and page["community"]["id"] == world["course"]
