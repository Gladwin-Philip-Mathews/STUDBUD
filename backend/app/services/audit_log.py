"""AuditLog (store D12, entity AuditRecord): append-only record of who did what (NFR-015, DR-015).

CD-1a AuditLog.record(actor, action, item, detail). Used by moderation (6.2, 6.4) and admin (9.0).
There is deliberately no update or delete operation.
"""
from datetime import datetime, timezone
from typing import Callable, Optional

from ..container import service


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog:
    def __init__(self, conn, clock: Callable[[], datetime] = utc_now):
        self.conn, self.clock = conn, clock

    def record(self, actor_id: Optional[int], action: str, item: str = "", detail: str = "") -> int:
        text = f"{item}: {detail}" if item and detail else (item or detail)
        cur = self.conn.execute(
            "INSERT INTO audit_records(at, actor_id, action, detail) VALUES (?,?,?,?)",
            (self.clock().isoformat(), actor_id, action, text))
        self.conn.commit()
        return cur.lastrowid

    def entries(self, action: Optional[str] = None) -> list:
        sql, args = "SELECT * FROM audit_records", ()
        if action:
            sql, args = sql + " WHERE action = ?", (action,)
        return [dict(r) for r in self.conn.execute(sql + " ORDER BY id", args).fetchall()]


@service("audit")
def build_audit_log(d):
    return AuditLog(d.db, **({"clock": d.clock} if d.clock else {}))
