"""Repositories for accepted domains (DR-013), the status counts (FR-103) and the pilot figures (process 8.0)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from ..models.pilot import AcceptedDomain, OnboardingAnswer


def _dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


def _s(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


class DomainRepository(ABC):
    @abstractmethod
    def list(self) -> list: ...
    @abstractmethod
    def add(self, domain): ...
    @abstractmethod
    def remove(self, domain: str) -> bool: ...
    @abstractmethod
    def exists(self, domain: str) -> bool: ...


class SuggestionRepository(ABC):
    @abstractmethod
    def add(self, name: str, account_id: int, at) -> int: ...
    @abstractmethod
    def get(self, suggestion_id: int): ...
    @abstractmethod
    def open_list(self) -> list: ...
    @abstractmethod
    def open_count_for(self, account_id: int) -> int: ...
    @abstractmethod
    def open_named(self, name: str) -> bool: ...
    @abstractmethod
    def set_status(self, suggestion_id: int, status: str) -> None: ...


class StatsRepository(ABC):
    @abstractmethod
    def status_counts(self, active_since) -> dict:
        """Accounts, active users since a time, posts, open reports and failed email messages (FR-103)."""


class OnboardingRepository(ABC):
    @abstractmethod
    def add(self, answer): ...
    @abstractmethod
    def find(self, account_id: int, week: int): ...
    @abstractmethod
    def all(self) -> list: ...


class PilotDataRepository(ABC):
    """Reads the raw rows the pilot report is computed from. No rule lives here (DD-10)."""
    @abstractmethod
    def students(self) -> list:
        """(account_id, cohort) for every verified student with a profile."""
    @abstractmethod
    def active_cohorts(self, since) -> list:
        """Cohort of every verified student who signed in since the given time."""
    @abstractmethod
    def request_rows(self) -> list:
        """One dict per connection request, including those kept after account deletion."""
    @abstractmethod
    def report_rows(self) -> list:
        """One dict per safety report with the reporter's cohort."""
    @abstractmethod
    def first_registration(self): ...


class SqliteDomainRepository(DomainRepository):
    def __init__(self, conn):
        self.conn = conn

    def list(self):
        rows = self.conn.execute("SELECT * FROM accepted_domains ORDER BY domain").fetchall()
        return [AcceptedDomain(r["domain"], _dt(r["added_at"]), r["added_by"]) for r in rows]

    def add(self, d):
        self.conn.execute("INSERT INTO accepted_domains(domain, added_at, added_by) VALUES (?,?,?)",
                          (d.domain, _s(d.added_at), d.added_by))
        self.conn.commit()
        return d

    def remove(self, domain):
        cur = self.conn.execute("DELETE FROM accepted_domains WHERE domain=?", (domain,))
        self.conn.commit()
        return cur.rowcount > 0

    def exists(self, domain):
        return self.conn.execute("SELECT 1 FROM accepted_domains WHERE domain=?", (domain,)).fetchone() is not None


class SqliteSuggestionRepository(SuggestionRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r):
        return {"id": r["id"], "name": r["name"], "suggestedBy": r["suggested_by"], "suggestedAt": r["suggested_at"],
                "status": r["status"]}

    def add(self, name, account_id, at):
        cur = self.conn.execute("INSERT INTO interest_suggestions(name, suggested_by, suggested_at) VALUES (?,?,?)",
                                (name, account_id, _s(at)))
        self.conn.commit()
        return cur.lastrowid

    def get(self, suggestion_id):
        r = self.conn.execute("SELECT * FROM interest_suggestions WHERE id=?", (suggestion_id,)).fetchone()
        return self._row(r) if r else None

    def open_list(self):
        rows = self.conn.execute("SELECT * FROM interest_suggestions WHERE status='open' ORDER BY id").fetchall()
        return [self._row(r) for r in rows]

    def open_count_for(self, account_id):
        return self.conn.execute("SELECT COUNT(*) FROM interest_suggestions WHERE status='open' AND suggested_by=?",
                                 (account_id,)).fetchone()[0]

    def open_named(self, name):
        return self.conn.execute("SELECT 1 FROM interest_suggestions WHERE status='open' AND lower(name)=lower(?)",
                                 (name,)).fetchone() is not None

    def set_status(self, suggestion_id, status):
        self.conn.execute("UPDATE interest_suggestions SET status=? WHERE id=?", (status, suggestion_id))
        self.conn.commit()


class SqliteStatsRepository(StatsRepository):
    def __init__(self, conn):
        self.conn = conn

    def _one(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()[0]

    def status_counts(self, active_since):
        return {
            "accounts": self._one("SELECT COUNT(*) FROM accounts WHERE status != 'deleted'"),
            "activeUsers": self._one("SELECT COUNT(*) FROM accounts WHERE status = 'verified' AND last_sign_in_at >= ?",
                                     _s(active_since)),
            "posts": self._one("SELECT COUNT(*) FROM posts WHERE status != 'deleted'"),
            "openReports": self._one("SELECT COUNT(*) FROM safety_reports WHERE status != 'closed'"),
            "failedEmails": self._one("SELECT COUNT(*) FROM notifications WHERE email_status = 'returned'"),
        }


class SqliteOnboardingRepository(OnboardingRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r):
        return OnboardingAnswer(r["account_id"], r["week"], r["answer"], r["cohort"], _dt(r["answered_at"]), r["id"])

    def add(self, a):
        cur = self.conn.execute("INSERT INTO onboarding_answers(account_id, week, answer, cohort, answered_at) VALUES (?,?,?,?,?)",
                                (a.account_id, a.week, a.answer, a.cohort, _s(a.answered_at)))
        self.conn.commit()
        a.id = cur.lastrowid
        return a

    def find(self, account_id, week):
        r = self.conn.execute("SELECT * FROM onboarding_answers WHERE account_id=? AND week=?", (account_id, week)).fetchone()
        return self._row(r) if r else None

    def all(self):
        return [self._row(r) for r in self.conn.execute("SELECT * FROM onboarding_answers ORDER BY id")]


class SqlitePilotDataRepository(PilotDataRepository):
    def __init__(self, conn):
        self.conn = conn

    def students(self):
        rows = self.conn.execute("SELECT a.id, p.cohort FROM accounts a JOIN profiles p ON p.account_id = a.id "
                                 "WHERE a.status = 'verified' AND a.role = 'student'").fetchall()
        return [(r["id"], r["cohort"]) for r in rows]

    def active_cohorts(self, since):
        rows = self.conn.execute("SELECT p.cohort FROM accounts a JOIN profiles p ON p.account_id = a.id "
                                 "WHERE a.status = 'verified' AND a.role = 'student' AND a.last_sign_in_at >= ?",
                                 (_s(since),)).fetchall()
        return [r["cohort"] for r in rows]

    def request_rows(self):
        live = self.conn.execute(
            "SELECT p.cohort AS cohort, p.intent AS intent, c.created_at AS sent_at, c.status AS outcome, "
            "c.status_changed_at AS outcome_at FROM connections c LEFT JOIN profiles p ON p.account_id = c.requester_id").fetchall()
        kept = self.conn.execute(
            "SELECT requester_cohort AS cohort, requester_intent AS intent, sent_at, outcome, outcome_at FROM request_timings").fetchall()
        return [{"cohort": r["cohort"], "intent": r["intent"], "sent_at": _dt(r["sent_at"]), "outcome": r["outcome"],
                 "outcome_at": _dt(r["outcome_at"])} for r in [*live, *kept]]

    def report_rows(self):
        rows = self.conn.execute(
            "SELECT p.cohort AS cohort, r.received_at, r.acknowledged_at, o.decision AS decision "
            "FROM safety_reports r LEFT JOIN profiles p ON p.account_id = r.reporter_id "
            "LEFT JOIN moderation_outcomes o ON o.report_id = r.id").fetchall()
        return [{"cohort": r["cohort"], "received_at": _dt(r["received_at"]),
                 "acknowledged_at": _dt(r["acknowledged_at"]), "decision": r["decision"]} for r in rows]

    def first_registration(self):
        r = self.conn.execute("SELECT MIN(created_at) m FROM accounts").fetchone()
        return _dt(r["m"]) if r and r["m"] else None
