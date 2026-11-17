from datetime import datetime, timedelta, timezone

from app.models import Account, AccountStatus, Connection, ConnectionStatus, Notification, Profile, VerificationToken
from app.models.enums import EventType

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)


def acct(**kw):
    return Account(email="a@g.rit.edu", display_name="Ana", password_hash="h", status=AccountStatus.VERIFIED, **kw)


def test_unverified_or_suspended_cannot_sign_in():  # FR-008, FR-009
    assert not Account("a@g.rit.edu", "A", "h").can_sign_in(NOW)
    a = acct(); a.suspend()
    assert not a.can_sign_in(NOW)
    assert acct().can_sign_in(NOW)


def test_lockout_after_five_failures_in_window():  # NFR-012 defaults
    a = acct()
    for i in range(5):
        a.record_failed_sign_in(NOW + timedelta(minutes=i), attempts=5, window_min=15, lock_min=15)
    assert a.is_locked(NOW + timedelta(minutes=5))
    assert not a.is_locked(NOW + timedelta(minutes=21))


def test_failures_outside_window_do_not_lock():
    a = acct()
    for i in range(5):
        a.record_failed_sign_in(NOW + timedelta(minutes=20 * i), attempts=5, window_min=15, lock_min=15)
    assert not a.is_locked(NOW + timedelta(minutes=90))


def test_successful_sign_in_resets_counters():
    a = acct(); a.record_failed_sign_in(NOW, 5, 15, 15)
    a.record_successful_sign_in(NOW)
    assert a.failed_sign_ins == 0 and a.last_sign_in_at == NOW


def test_token_validity():  # FR-005, FR-006
    t = VerificationToken(1, "h", expires_at=NOW + timedelta(hours=1))
    assert t.is_valid(NOW)
    assert not t.is_valid(NOW + timedelta(hours=2))
    t.used_at = NOW
    assert not t.is_valid(NOW)


def test_connection_lifecycle_sets_status_and_time():
    c = Connection(1, 2)
    assert c.is_open()
    c.accept(NOW)
    assert c.status == ConnectionStatus.ACCEPTED and c.status_changed_at == NOW and c.is_open()
    c.remove(NOW)
    assert not c.is_open()


def test_shared_items_count_courses_and_interests():
    a = Profile(1, interests=["Chess", "AI"], course_codes=["SWEN-261"])
    b = Profile(2, interests=["chess"], course_codes=["SWEN-261", "MATH-101"])
    assert a.shared_items_with(b) == 2


def test_resend_limit_is_three():  # CH-15, AC-FR-084a
    n = Notification(1, EventType.REQUEST_RECEIVED, "x")
    for _ in range(3):
        assert n.can_resend(); n.email_resends += 1
    assert not n.can_resend()
