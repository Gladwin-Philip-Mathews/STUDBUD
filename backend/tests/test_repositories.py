from datetime import datetime, timedelta, timezone

import pytest
import sqlite3

from app.models import Account, AccountStatus, Connection, ConnectionStatus, Notification, Profile, VerificationToken
from app.models.enums import EmailStatus, EventType
from app.repositories import (
    SqliteAccountRepository, SqliteConnectionRepository, SqliteNotificationRepository,
    SqliteProfileRepository, SqliteVerificationTokenRepository,
)

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)


def make(conn, email="a@g.rit.edu", name="Ana"):
    return SqliteAccountRepository(conn).add(Account(email, name, "hash"))


def test_account_roundtrip_and_lowercase_email(conn):
    repo = SqliteAccountRepository(conn)
    a = make(conn, "Ana@G.RIT.edu")
    got = repo.find_by_email("ANA@g.rit.edu")
    assert got.id == a.id and got.email == "ana@g.rit.edu"


def test_email_and_display_name_unique(conn):  # DR-001
    make(conn)
    with pytest.raises(sqlite3.IntegrityError):
        make(conn, "A@g.rit.edu", "Other")
    with pytest.raises(sqlite3.IntegrityError):
        make(conn, "b@g.rit.edu", "ana")


def test_domain_check_uses_accepted_domains(conn):  # FR-101
    repo = SqliteAccountRepository(conn)
    assert repo.domain_accepted("x@g.rit.edu")
    assert not repo.domain_accepted("x@gmail.com")


def test_save_persists_lockout_fields(conn):
    repo = SqliteAccountRepository(conn)
    a = make(conn)
    a.status = AccountStatus.VERIFIED
    a.record_failed_sign_in(NOW, 1, 15, 15)
    repo.save(a)
    got = repo.get(a.id)
    assert got.status == AccountStatus.VERIFIED and got.locked_until is not None


def test_token_store_and_resend_window(conn):  # NFR-012 resend limit
    a = make(conn)
    repo = SqliteVerificationTokenRepository(conn)
    for i in range(3):
        repo.add(VerificationToken(a.id, f"h{i}", NOW + timedelta(hours=24), created_at=NOW + timedelta(minutes=i),
                                   is_resend=i > 0))
    assert repo.count_resends_since(a.id, NOW - timedelta(hours=1)) == 2
    assert repo.count_resends_since(a.id, NOW + timedelta(minutes=2)) == 1
    t = repo.find_by_hash("h1")
    t.used_at = NOW
    repo.save(t)
    assert repo.find_by_hash("h1").used_at == NOW


def test_tokens_removed_with_account(conn):  # composition (DD-07)
    a = make(conn)
    repo = SqliteVerificationTokenRepository(conn)
    repo.add(VerificationToken(a.id, "h", NOW + timedelta(hours=1)))
    conn.execute("DELETE FROM accounts WHERE id = ?", (a.id,))
    assert repo.find_by_hash("h") is None


def test_profile_roundtrip_and_interest_limit(conn):
    a = make(conn)
    repo = SqliteProfileRepository(conn)
    repo.save(Profile(a.id, "study partner", "first year", 1, ["AI", "Chess"], ["SWEN-261"]))
    p = repo.get(a.id)
    assert p.interests == ["AI", "Chess"] and p.course_codes == ["SWEN-261"] and p.intent == "study partner"
    with pytest.raises(ValueError):
        repo.save(Profile(a.id, interests=[f"i{n}" for n in range(21)]))


def test_connection_between_either_direction_and_status_update(conn):
    a, b = make(conn), make(conn, "b@g.rit.edu", "Ben")
    repo = SqliteConnectionRepository(conn)
    c = repo.add(Connection(a.id, b.id, note="hi"))
    assert [x.id for x in repo.between(b.id, a.id)] == [c.id]
    c.decline(NOW)
    repo.save(c)
    got = repo.get(c.id)
    assert got.status == ConnectionStatus.DECLINED and got.status_changed_at == NOW


def test_connection_keeps_row_after_account_deleted(conn):  # FR-091
    a, b = make(conn), make(conn, "b@g.rit.edu", "Ben")
    repo = SqliteConnectionRepository(conn)
    c = repo.add(Connection(a.id, b.id))
    conn.execute("DELETE FROM accounts WHERE id = ?", (a.id,))
    got = repo.get(c.id)
    assert got is not None and got.requester_id is None


def test_notification_resend_counter_limited_to_three(conn):  # CH-15
    a = make(conn)
    repo = SqliteNotificationRepository(conn)
    n = repo.add(Notification(a.id, EventType.REQUEST_RECEIVED, "Ben sent you a request"))
    n.email_resends = 3
    n.email_status = EmailStatus.RETURNED
    repo.save(n)
    assert repo.get(n.id).email_resends == 3
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE notifications SET email_resends = 4 WHERE id = ?", (n.id,))
