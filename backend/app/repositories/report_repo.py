"""ReportRepository (D8 Moderation Log)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from ..models.moderation import ModerationOutcome, SafetyReport


def _dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


def _s(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


class ReportRepository(ABC):
    @abstractmethod
    def save(self, report): ...
    @abstractmethod
    def get(self, report_id: int): ...
    @abstractmethod
    def find_open(self) -> list:
        """Reports without an outcome, oldest first (CD-1a findOpen)."""
    @abstractmethod
    def save_outcome(self, outcome) -> None: ...
    @abstractmethod
    def get_outcome(self, report_id: int): ...
    @abstractmethod
    def add_note(self, report_id: int, note: str, added_at, moderator_id: int) -> None: ...
    @abstractmethod
    def protected_message_ids(self, recent_since) -> set:
        """Messages attached to an open report or one closed since `recent_since` (OR-001)."""
    @abstractmethod
    def purge_closed_before(self, cutoff) -> int:
        """Delete closed reports decided before `cutoff`, with their outcome and notes (OR-002). Returns how many.
        Open reports are never deleted. The only caller is the retention clean-up (RetentionService)."""


class SqliteReportRepository(ReportRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r):
        return SafetyReport(reporter_id=r["reporter_id"], reported_student_id=r["reported_student_id"],
                            item_type=r["item_type"], item_id=r["item_id"], reason=r["reason"], text=r["text"],
                            received_at=_dt(r["received_at"]), status=r["status"],
                            acknowledged_at=_dt(r["acknowledged_at"]), acknowledged_by=r["acknowledged_by"], id=r["id"])

    def save(self, rep):
        if rep.id is None:
            cur = self.conn.execute(
                "INSERT INTO safety_reports(reporter_id, reported_student_id, item_type, item_id, reason, text, "
                "received_at, status) VALUES (?,?,?,?,?,?,?,?)",
                (rep.reporter_id, rep.reported_student_id, rep.item_type, rep.item_id, rep.reason, rep.text,
                 _s(rep.received_at), rep.status))
            rep.id = cur.lastrowid
        else:
            self.conn.execute("UPDATE safety_reports SET status=?, acknowledged_at=?, acknowledged_by=? WHERE id=?",
                              (rep.status, _s(rep.acknowledged_at), rep.acknowledged_by, rep.id))
        self.conn.commit()
        return rep

    def get(self, report_id):
        r = self.conn.execute("SELECT * FROM safety_reports WHERE id=?", (report_id,)).fetchone()
        return self._row(r) if r else None

    def find_open(self):
        rows = self.conn.execute(
            "SELECT * FROM safety_reports WHERE status != 'closed' ORDER BY received_at, id").fetchall()
        return [self._row(r) for r in rows]

    def save_outcome(self, o):
        self.conn.execute("INSERT INTO moderation_outcomes(report_id, decision, action, note, decided_at, moderator_id) "
                          "VALUES (?,?,?,?,?,?)", (o.report_id, o.decision, o.action, o.note, _s(o.decided_at), o.moderator_id))
        self.conn.execute("UPDATE safety_reports SET status='closed' WHERE id=?", (o.report_id,))
        self.conn.commit()

    def get_outcome(self, report_id):
        r = self.conn.execute("SELECT * FROM moderation_outcomes WHERE report_id=?", (report_id,)).fetchone()
        if not r:
            return None
        o = ModerationOutcome(report_id=report_id, decision=r["decision"], action=r["action"], note=r["note"],
                              decided_at=_dt(r["decided_at"]), moderator_id=r["moderator_id"])
        for n in self.conn.execute("SELECT * FROM outcome_notes WHERE report_id=? ORDER BY id", (report_id,)):
            o.add_later_note(n["note"], _dt(n["added_at"]), n["moderator_id"])
        return o

    def add_note(self, report_id, note, added_at, moderator_id):
        self.conn.execute("INSERT INTO outcome_notes(report_id, note, added_at, moderator_id) VALUES (?,?,?,?)",
                          (report_id, note, _s(added_at), moderator_id))
        self.conn.commit()

    def protected_message_ids(self, recent_since):
        rows = self.conn.execute(
            "SELECT r.item_id FROM safety_reports r LEFT JOIN moderation_outcomes o ON o.report_id = r.id "
            "WHERE r.item_type='message' AND (o.report_id IS NULL OR o.decided_at >= ?)", (_s(recent_since),)).fetchall()
        return {r["item_id"] for r in rows if r["item_id"] is not None}

    def purge_closed_before(self, cutoff):
        rows = self.conn.execute(
            "SELECT report_id FROM moderation_outcomes WHERE decided_at < ?", (_s(cutoff),)).fetchall()
        doomed = [(r["report_id"],) for r in rows]
        if not doomed:
            return 0
        # The append-only triggers (FR-067) stand down only while the unlock row exists, inside this transaction.
        self.conn.execute("INSERT OR IGNORE INTO retention_unlock(id) VALUES (1)")
        try:
            self.conn.executemany("DELETE FROM outcome_notes WHERE report_id=?", doomed)
            self.conn.executemany("DELETE FROM moderation_outcomes WHERE report_id=?", doomed)
            self.conn.executemany("DELETE FROM safety_reports WHERE id=?", doomed)
        finally:
            self.conn.execute("DELETE FROM retention_unlock")
        self.conn.commit()
        return len(doomed)
