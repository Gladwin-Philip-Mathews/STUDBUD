"""SQLite implementations of the repository interfaces."""
from datetime import datetime, timezone
from typing import Optional

from ..models.entities import Account, Connection, Notification, Profile, VerificationToken
from ..models.enums import AccountStatus, ConnectionStatus, EmailStatus, EventType, Role
from .interfaces import (
    AccountRepository, ConnectionRepository, NotificationRepository,
    ProfileRepository, VerificationTokenRepository,
)


def _dt(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


def _s(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteAccountRepository(AccountRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r) -> Account:
        return Account(
            id=r["id"], email=r["email"], display_name=r["display_name"], password_hash=r["password_hash"],
            status=AccountStatus(r["status"]), role=Role(r["role"]), failed_sign_ins=r["failed_sign_ins"],
            first_failed_at=_dt(r["first_failed_at"]), locked_until=_dt(r["locked_until"]),
            last_sign_in_at=_dt(r["last_sign_in_at"]), email_notifications=bool(r["email_notifications"]),
            created_at=_dt(r["created_at"]),
        )

    def add(self, a: Account) -> Account:
        a.created_at = a.created_at or _now()
        a.email = a.email.strip().lower()
        cur = self.conn.execute(
            "INSERT INTO accounts(email, display_name, password_hash, status, role, created_at) VALUES (?,?,?,?,?,?)",
            (a.email, a.display_name, a.password_hash, a.status.value, a.role.value, _s(a.created_at)),
        )
        a.id = cur.lastrowid
        self.conn.commit()
        return a

    def get(self, account_id):
        r = self.conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return self._row(r) if r else None

    def find_by_email(self, email):
        r = self.conn.execute("SELECT * FROM accounts WHERE email = ?", (email.strip().lower(),)).fetchone()
        return self._row(r) if r else None

    def display_name_taken(self, display_name):
        return self.conn.execute("SELECT 1 FROM accounts WHERE display_name = ?", (display_name,)).fetchone() is not None

    def save(self, a: Account):
        self.conn.execute(
            "UPDATE accounts SET display_name=?, password_hash=?, status=?, role=?, failed_sign_ins=?, "
            "first_failed_at=?, locked_until=?, last_sign_in_at=?, email_notifications=? WHERE id=?",
            (a.display_name, a.password_hash, a.status.value, a.role.value, a.failed_sign_ins,
             _s(a.first_failed_at), _s(a.locked_until), _s(a.last_sign_in_at), int(a.email_notifications), a.id),
        )
        self.conn.commit()

    def domain_accepted(self, email):
        domain = email.strip().lower().rpartition("@")[2]
        return self.conn.execute("SELECT 1 FROM accepted_domains WHERE domain = ?", (domain,)).fetchone() is not None


class SqliteVerificationTokenRepository(VerificationTokenRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r):
        return VerificationToken(id=r["id"], account_id=r["account_id"], token_hash=r["token_hash"],
                                 expires_at=_dt(r["expires_at"]), created_at=_dt(r["created_at"]),
                                 used_at=_dt(r["used_at"]), is_resend=bool(r["is_resend"]))

    def add(self, t):
        t.created_at = t.created_at or _now()
        cur = self.conn.execute(
            "INSERT INTO verification_tokens(account_id, token_hash, created_at, expires_at, is_resend) VALUES (?,?,?,?,?)",
            (t.account_id, t.token_hash, _s(t.created_at), _s(t.expires_at), int(t.is_resend)))
        t.id = cur.lastrowid
        self.conn.commit()
        return t

    def find_by_hash(self, token_hash):
        r = self.conn.execute("SELECT * FROM verification_tokens WHERE token_hash = ?", (token_hash,)).fetchone()
        return self._row(r) if r else None

    def save(self, t):
        self.conn.execute("UPDATE verification_tokens SET used_at=?, expires_at=? WHERE id=?",
                          (_s(t.used_at), _s(t.expires_at), t.id))
        self.conn.commit()

    def count_resends_since(self, account_id, since):
        r = self.conn.execute(
            "SELECT COUNT(*) AS n FROM verification_tokens WHERE account_id = ? AND is_resend = 1 AND created_at >= ?",
            (account_id, _s(since))).fetchone()
        return r["n"]

    def invalidate_all(self, account_id, now):
        self.conn.execute("UPDATE verification_tokens SET used_at = ? WHERE account_id = ? AND used_at IS NULL",
                          (_s(now), account_id))
        self.conn.commit()


class SqliteProfileRepository(ProfileRepository):
    def __init__(self, conn):
        self.conn = conn

    def get(self, account_id):
        r = self.conn.execute("SELECT * FROM profiles WHERE account_id = ?", (account_id,)).fetchone()
        if not r:
            return None
        interests = [x["interest"] for x in self.conn.execute(
            "SELECT interest FROM profile_interests WHERE account_id = ? ORDER BY interest", (account_id,))]
        courses = [x["course_code"] for x in self.conn.execute(
            "SELECT course_code FROM profile_courses WHERE account_id = ? ORDER BY course_code", (account_id,))]
        return Profile(account_id=account_id, intent=r["intent"], cohort=r["cohort"],
                       year_of_study=r["year_of_study"], interests=interests, course_codes=courses)

    def save(self, p: Profile):
        if len(p.interests) > 20:
            raise ValueError("A profile has at most 20 interests (DR-002)")
        c = self.conn
        c.execute(
            "INSERT INTO profiles(account_id, intent, cohort, year_of_study) VALUES (?,?,?,?) "
            "ON CONFLICT(account_id) DO UPDATE SET intent=excluded.intent, cohort=excluded.cohort, "
            "year_of_study=excluded.year_of_study",
            (p.account_id, p.intent, p.cohort, p.year_of_study))
        c.execute("DELETE FROM profile_interests WHERE account_id = ?", (p.account_id,))
        c.executemany("INSERT INTO profile_interests(account_id, interest) VALUES (?,?)",
                      [(p.account_id, i) for i in dict.fromkeys(p.interests)])
        c.execute("DELETE FROM profile_courses WHERE account_id = ?", (p.account_id,))
        c.executemany("INSERT INTO profile_courses(account_id, course_code) VALUES (?,?)",
                      [(p.account_id, code) for code in dict.fromkeys(p.course_codes)])
        c.commit()


    def candidates(self, exclude_id):
        accounts = SqliteAccountRepository(self.conn)
        rows = self.conn.execute(
            "SELECT p.account_id FROM profiles p JOIN accounts a ON a.id = p.account_id "
            "WHERE a.status = 'verified' AND a.id != ? ORDER BY a.id", (exclude_id,)).fetchall()
        return [(accounts.get(r["account_id"]), self.get(r["account_id"])) for r in rows]


class SqliteConnectionRepository(ConnectionRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r):
        return Connection(id=r["id"], requester_id=r["requester_id"], receiver_id=r["receiver_id"],
                          status=ConnectionStatus(r["status"]), note=r["note"],
                          created_at=_dt(r["created_at"]), status_changed_at=_dt(r["status_changed_at"]))

    def add(self, c: Connection):
        c.created_at = c.created_at or _now()
        c.status_changed_at = c.status_changed_at or c.created_at
        cur = self.conn.execute(
            "INSERT INTO connections(requester_id, receiver_id, status, note, created_at, status_changed_at) "
            "VALUES (?,?,?,?,?,?)",
            (c.requester_id, c.receiver_id, c.status.value, c.note, _s(c.created_at), _s(c.status_changed_at)))
        c.id = cur.lastrowid
        self.conn.commit()
        return c

    def get(self, connection_id):
        r = self.conn.execute("SELECT * FROM connections WHERE id = ?", (connection_id,)).fetchone()
        return self._row(r) if r else None

    def between(self, a_id, b_id):
        rows = self.conn.execute(
            "SELECT * FROM connections WHERE (requester_id=? AND receiver_id=?) OR (requester_id=? AND receiver_id=?) "
            "ORDER BY id", (a_id, b_id, b_id, a_id)).fetchall()
        return [self._row(r) for r in rows]

    def find_open_between(self, a_id, b_id):
        for c in self.between(a_id, b_id):
            if c.is_open():
                return c
        return None

    def last_decline_by(self, receiver_id, sender_id):
        row = self.conn.execute(
            "SELECT MAX(status_changed_at) AS at FROM connections WHERE status='declined' "
            "AND requester_id=? AND receiver_id=?", (sender_id, receiver_id)).fetchone()
        return _dt(row["at"]) if row and row["at"] else None

    def for_account(self, account_id):
        rows = self.conn.execute(
            "SELECT * FROM connections WHERE requester_id=? OR receiver_id=? ORDER BY id", (account_id, account_id)).fetchall()
        return [self._row(r) for r in rows]

    def save(self, c: Connection):
        self.conn.execute("UPDATE connections SET status=?, note=?, status_changed_at=? WHERE id=?",
                          (c.status.value, c.note, _s(c.status_changed_at), c.id))
        self.conn.commit()


    def dismiss(self, account_id, dismissed_id):
        self.conn.execute("INSERT OR IGNORE INTO dismissed_suggestions(account_id, dismissed_id) VALUES (?,?)",
                          (account_id, dismissed_id))
        self.conn.commit()

    def dismissed_ids(self, account_id):
        return {r["dismissed_id"] for r in self.conn.execute(
            "SELECT dismissed_id FROM dismissed_suggestions WHERE account_id = ?", (account_id,))}


class SqliteNotificationRepository(NotificationRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r):
        return Notification(id=r["id"], recipient_id=r["recipient_id"], event_type=EventType(r["event_type"]),
                            body=r["body"], created_at=_dt(r["created_at"]), read_at=_dt(r["read_at"]),
                            email_status=EmailStatus(r["email_status"]), email_resends=r["email_resends"])

    def add(self, n: Notification):
        n.created_at = n.created_at or _now()
        cur = self.conn.execute(
            "INSERT INTO notifications(recipient_id, event_type, body, created_at, email_status, email_resends) "
            "VALUES (?,?,?,?,?,?)",
            (n.recipient_id, n.event_type.value, n.body, _s(n.created_at), n.email_status.value, n.email_resends))
        n.id = cur.lastrowid
        self.conn.commit()
        return n

    def get(self, notification_id):
        r = self.conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        return self._row(r) if r else None

    def for_recipient(self, account_id):
        rows = self.conn.execute("SELECT * FROM notifications WHERE recipient_id = ? ORDER BY id DESC", (account_id,)).fetchall()
        return [self._row(r) for r in rows]

    def save(self, n: Notification):
        self.conn.execute("UPDATE notifications SET read_at=?, email_status=?, email_resends=? WHERE id=?",
                          (_s(n.read_at), n.email_status.value, n.email_resends, n.id))
        self.conn.commit()

    def pending_email(self):
        rows = self.conn.execute(
            "SELECT * FROM notifications WHERE email_status IN ('not sent', 'returned') AND email_resends <= 3 ORDER BY id"
        ).fetchall()
        return [self._row(r) for r in rows]

    def mark_all_read(self, account_id, now):
        self.conn.execute("UPDATE notifications SET read_at = ? WHERE recipient_id = ? AND read_at IS NULL",
                          (_s(now), account_id))
        self.conn.commit()
