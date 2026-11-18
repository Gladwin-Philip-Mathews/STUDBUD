from datetime import timedelta

import pytest

from app.container import get_service
from app.db import connect
from app.models import Profile

from .helpers import PASSWORD, make_student, signed_in_client


def sql(app, query, *args):
    conn = connect(app.config["DATABASE_PATH"])
    conn.execute(query, args)
    conn.commit()
    conn.close()


def iso(clock, **ago):
    return (clock() - timedelta(**ago)).isoformat()


@pytest.fixture
def admin(app):
    aid = make_student(app, "Root")
    sql(app, "UPDATE accounts SET role='administrator' WHERE id=?", aid)
    return signed_in_client(app, "Root")


def answer(client, value):
    return client.post("/api/onboarding/answer", json={"answer": value})


def test_report_states_its_period_and_the_records_used(app):  # NFR-024
    from app.container import get_service
    with app.app_context():
        data = get_service("pilot").report()
        assert set(data["period"]) == {"from", "to"} and isinstance(data["records"], int)
        assert "period_from" in get_service("pilot").report_csv()


def test_question_is_asked_once_and_skipping_is_recorded(app, clock):  # AC-FR-090a
    sid = make_student(app, "Stu")
    sql(app, "UPDATE accounts SET created_at=? WHERE id=?", iso(clock, days=3), sid)
    stu = signed_in_client(app, "Stu")
    q = stu.get("/api/onboarding/question").get_json()["question"]
    assert q["week"] == 1 and "speak with regularly" in q["text"] and q["choices"] == ["0", "1 to 2", "3 to 5", "more than 5"]
    assert answer(stu, "skipped").status_code == 201
    assert stu.get("/api/onboarding/question").get_json()["question"] is None  # shown once
    assert answer(stu, "3 to 5").status_code == 400
    with app.app_context():
        stored = get_service("pilot").onboarding.find(sid, 1)
    assert stored.answer == "skipped" and stored.cohort == "prefer not to say"


def test_no_question_for_an_invalid_answer(app, clock):
    sid = make_student(app, "Stu")
    sql(app, "UPDATE accounts SET created_at=? WHERE id=?", iso(clock, days=1), sid)
    assert answer(signed_in_client(app, "Stu"), "lots").status_code == 400


def test_question_is_asked_again_in_week_12_and_both_answers_are_stored(app, clock):  # AC-FR-090b
    sid = make_student(app, "Stu")
    sql(app, "UPDATE accounts SET created_at=? WHERE id=?", clock().isoformat(), sid)
    stu = signed_in_client(app, "Stu")
    assert answer(stu, "0").status_code == 201
    clock.advance(days=40)
    assert signed_in_client(app, "Stu").get("/api/onboarding/question").get_json()["question"] is None  # week 6
    clock.advance(days=40)  # day 80: week 12
    stu = signed_in_client(app, "Stu")
    assert stu.get("/api/onboarding/question").get_json()["question"]["week"] == 12
    assert answer(stu, "3 to 5").status_code == 201
    with app.app_context():
        repo = get_service("pilot").onboarding
        assert repo.find(sid, 1).answer == "0" and repo.find(sid, 12).answer == "3 to 5"
    assert stu.get("/api/onboarding/question").get_json()["question"] is None


def test_request_timing_is_kept_without_identity_after_deletion(app, clock):  # AC-FR-091a
    a = make_student(app, "Ann", profile=Profile(0, intent="study partner", cohort="first year"))
    b = make_student(app, "Ben")
    ann, ben = signed_in_client(app, "Ann"), signed_in_client(app, "Ben")
    cid = ann.post("/api/connections/requests", json={"receiverId": b}).get_json()["connection"]["id"]
    clock.advance(hours=6)
    ben = signed_in_client(app, "Ben")
    ben.post(f"/api/connections/{cid}/accept")
    ann = signed_in_client(app, "Ann")
    assert ann.delete("/api/profile", json={"password": PASSWORD}).status_code == 200
    conn = connect(app.config["DATABASE_PATH"])
    row = conn.execute("SELECT * FROM request_timings").fetchone()
    conn.close()
    assert row["outcome"] == "accepted" and row["sent_at"] and row["outcome_at"]
    assert set(row.keys()) == {"id", "sent_at", "outcome", "outcome_at", "requester_cohort", "requester_intent"}  # no identity


def build_data_set(app, clock, cohort="first year"):
    """10 study partner requests (6 accepted within 7 days), 8 reports (7 acknowledged within 48 hours),
    40 active users and 1 upheld report. Expected: 60%, 87.5% and 2.5 per 100 (AC-FR-092a)."""
    users = [make_student(app, f"U{n:02d}", profile=Profile(0, intent="study partner", cohort=cohort)) for n in range(40)]
    now = clock().isoformat()
    conn = connect(app.config["DATABASE_PATH"])
    conn.execute("UPDATE accounts SET last_sign_in_at=?", (now,))
    for n in range(10):
        within = n < 6
        sent = clock() - timedelta(days=20)
        outcome_at = sent + (timedelta(days=3) if within else timedelta(days=9))
        status = "accepted" if n < 8 else "declined"
        conn.execute("INSERT INTO connections(requester_id, receiver_id, status, created_at, status_changed_at) VALUES (?,?,?,?,?)",
                     (users[n], users[n + 10], status, sent.isoformat(), outcome_at.isoformat()))
    for n in range(8):
        received = clock() - timedelta(days=5)
        ack = (received + timedelta(hours=10 if n < 7 else 60)).isoformat()
        cur = conn.execute("INSERT INTO safety_reports(reporter_id, reported_student_id, item_type, item_id, reason, text, "
                           "received_at, status, acknowledged_at) VALUES (?,?,?,?,?,?,?,?,?)",
                           (users[n], users[n + 20], "student", users[n + 20], "spam", "", received.isoformat(), "closed", ack))
        if n == 0:
            conn.execute("INSERT INTO moderation_outcomes(report_id, decision, action, note, decided_at, moderator_id) "
                         "VALUES (?,?,?,?,?,?)", (cur.lastrowid, "upheld", "warning", "n", now, users[0]))
        else:
            conn.execute("INSERT INTO moderation_outcomes(report_id, decision, action, note, decided_at, moderator_id) "
                         "VALUES (?,?,?,?,?,?)", (cur.lastrowid, "dismissed", "none", "n", now, users[0]))
    conn.commit()
    conn.close()
    return users


def test_report_figures_match_the_hand_calculation(app, clock, admin):  # AC-FR-092a
    build_data_set(app, clock)
    r = admin.get("/api/admin/pilot-report").get_json()
    group = next(g for g in r["groups"] if g["cohort"] == "first year")
    assert group["requests_sent"] == 10 and group["accepted_within_7_days_pct"] == 60.0
    assert group["safety_reports"] == 8 and group["acknowledged_within_48h_pct"] == 87.5
    assert group["active_users"] == 40 and group["upheld_reports"] == 1 and group["upheld_per_100_active"] == 2.5
    assert r["weekly"]  # the report is also given by week


def test_change_between_week_1_and_week_12(app, clock, admin):  # FR-092 (G-02)
    users = [make_student(app, f"S{n}", profile=Profile(0, cohort="international")) for n in range(5)]
    with app.app_context():
        repo = get_service("pilot").onboarding
        from app.models import OnboardingAnswer
        for n, (first, second) in enumerate([("0", "1 to 2"), ("1 to 2", "1 to 2"), ("3 to 5", "more than 5"),
                                             ("skipped", "3 to 5"), ("more than 5", "0")]):
            repo.add(OnboardingAnswer(users[n], 1, first, "international", clock()))
            repo.add(OnboardingAnswer(users[n], 12, second, "international", clock()))
    g = next(x for x in admin.get("/api/admin/pilot-report").get_json()["groups"] if x["cohort"] == "international")
    assert g["answered_both"] == 5 and g["contact_increased"] == 2  # skipped is left out of the change
    assert g["week1_answers"]["0"] == 1 and g["week12_answers"]["1 to 2"] == 2


def test_a_group_under_five_is_combined_not_shown_alone(app, clock, admin):  # AC-FR-093a
    for n in range(6):
        make_student(app, f"Big{n}", profile=Profile(0, cohort="first year"))
    for n in range(4):
        make_student(app, f"Few{n}", profile=Profile(0, cohort="international"))
    names = [g["cohort"] for g in admin.get("/api/admin/pilot-report").get_json()["groups"]]
    assert "international" not in names
    assert any(n.startswith("other") for n in names)


def test_merge_rules():  # FR-093
    from app.services.pilot_service import merge_small_groups
    assert merge_small_groups({"a": 10, "b": 3, "c": 4}) == {"a": "a", "b": "other", "c": "other"}
    assert merge_small_groups({"a": 10, "b": 4}) == {"a": "other + a", "b": "other + a"}
    assert merge_small_groups({"a": 10, "b": 6}) == {"a": "a", "b": "b"}


def test_export_has_no_names_or_email_addresses(app, clock, admin):  # AC-FR-094a
    build_data_set(app, clock)
    r = admin.get("/api/admin/pilot-report.csv")
    assert r.status_code == 200 and r.mimetype == "text/csv"
    text = r.get_data(as_text=True)
    assert "first year" in text and "@" not in text and "U00" not in text and "Root" not in text


def test_pilot_report_is_for_administrators_only(app):  # NFR-013
    make_student(app, "Stu")
    assert signed_in_client(app, "Stu").get("/api/admin/pilot-report").status_code == 403
