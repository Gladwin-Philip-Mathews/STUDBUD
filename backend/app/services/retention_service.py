"""RetentionService: the clean-up run that applies OR-001 and OR-002.

M3 DD-09 says content is removed physically only by the retention rules; this is where those rules run. Nothing in
the product called them before this service existed, so the periods in MESSAGE_RETENTION and LOG_RETENTION had no
effect. The run is started by an administrator (POST /api/admin/clean-up) or from the shell (`flask --app app
clean-up`, for a daily scheduled job on the host).

OR-001: messages older than MESSAGE_RETENTION are deleted unless they are named in an open or recent safety report.
OR-002: closed reports, their outcomes and notes, and audit records older than LOG_RETENTION are deleted. Open reports
are never deleted. Both periods are settings (NFR-012, CH-15), so AC-OR-002a (period set to 1 day) needs no release.
Each run writes one audit entry with the counts (NFR-015).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from ..container import service
from ..models.enums import SettingName


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CleanUpResult:
    messages_deleted: int
    reports_deleted: int
    audit_entries_deleted: int
    ran_at: datetime

    def as_dict(self) -> dict:
        return {"messagesDeleted": self.messages_deleted, "reportsDeleted": self.reports_deleted,
                "auditEntriesDeleted": self.audit_entries_deleted, "ranAt": self.ran_at.isoformat()}


class RetentionService:
    def __init__(self, messaging, moderation, reports, audit, settings, clock: Callable[[], datetime] = utc_now):
        self.messaging, self.moderation, self.reports = messaging, moderation, reports
        self.audit, self.settings, self.clock = audit, settings, clock

    def run(self, actor_id: Optional[int] = None) -> CleanUpResult:
        now = self.clock()
        # OR-001: messages, except those an open or recent report still needs
        messages = self.messaging.apply_retention(self.moderation.retention_keep_ids())
        # OR-002: conduct records
        log_cutoff = now - self.settings.duration(SettingName.LOG_RETENTION)
        reports = self.reports.purge_closed_before(log_cutoff)
        audit_entries = self.audit.purge_before(log_cutoff)
        self.audit.record(actor_id, "CLEAN_UP", "retention",
                          f"messages {messages}, reports {reports}, audit entries {audit_entries}")
        return CleanUpResult(messages, reports, audit_entries, now)


@service("retention")
def build_retention_service(d):
    from ..container import get_service
    kwargs = {"clock": d.clock} if d.clock else {}
    return RetentionService(get_service("messaging"), get_service("moderation"), d.reports, get_service("audit"),
                            d.settings, **kwargs)
