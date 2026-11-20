"""AuditLog (store D12, entity AuditRecord): append-only record of who did what (NFR-015, DR-015).

CD-1b AuditLog.record(actor, action, item: ItemRef). Used by moderation (6.2, 6.4), administration (9.0), staff
sign-in (1.0) and the retention clean-up. There is deliberately no update operation; the only deletion is the
retention clean-up of OR-002, which runs as the system.
"""
from datetime import datetime, timezone
from typing import Callable, Optional

from ..container import service
from ..models.pilot import AuditRecord


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog:
    def __init__(self, conn, clock: Callable[[], datetime] = utc_now):
        self.conn, self.clock = conn, clock

    def record(self, actor_id: Optional[int], action: str, item="", detail: str = "") -> int:
        """Append one entry. `item` is an ItemRef or its text form ("report 12", "post:4")."""
        cur = self.conn.execute(
            "INSERT INTO audit_records(at, actor_id, action, item_ref, detail) VALUES (?,?,?,?,?)",
            (self.clock().isoformat(), actor_id, action, str(item or ""), detail or ""))
        self.conn.commit()
        return cur.lastrowid

    def purge_before(self, cutoff: datetime) -> int:
        """OR-002: remove entries older than the conduct record retention period. Only the retention clean-up calls
        this; it is not reachable from any page or endpoint on its own."""
        cur = self.conn.execute("DELETE FROM audit_records WHERE at < ?", (cutoff.isoformat(),))
        self.conn.commit()
        return cur.rowcount

    def entries(self, action: Optional[str] = None) -> list:
        sql, args = "SELECT * FROM audit_records", ()
        if action:
            sql, args = sql + " WHERE action = ?", (action,)
        rows = self.conn.execute(sql + " ORDER BY id", args).fetchall()
        return [AuditRecord(at=datetime.fromisoformat(r["at"]), actor_id=r["actor_id"], action=r["action"],
                            item_ref=r["item_ref"] or "", detail=r["detail"] or "", id=r["id"]) for r in rows]


@service("audit")
def build_audit_log(d):
    return AuditLog(d.db, **({"clock": d.clock} if d.clock else {}))
