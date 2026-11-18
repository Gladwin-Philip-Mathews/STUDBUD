"""SafetyReport and ModerationOutcome (CD-1b)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class SafetyReport:
    reporter_id: int
    reported_student_id: int
    item_type: str  # student | post | reply | message
    item_id: Optional[int]
    reason: str
    text: str
    received_at: datetime
    status: str = "open"
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    id: Optional[int] = None

    def acknowledge(self, now: datetime, moderator_id: int) -> bool:
        """Records time and moderator, keeps the report open (FR-063). A second acknowledgement changes nothing."""
        if self.acknowledged_at is not None or self.status == "closed":
            return False
        self.acknowledged_at, self.acknowledged_by, self.status = now, moderator_id, "acknowledged"
        return True

    def is_overdue(self, now: datetime, limit: timedelta) -> bool:
        """Unacknowledged after the overdue setting, 36 hours by default (FR-062, NFR-012)."""
        return self.acknowledged_at is None and self.status != "closed" and now - self.received_at >= limit


@dataclass
class ModerationOutcome:
    report_id: int
    decision: str
    action: str
    note: str
    decided_at: datetime
    moderator_id: int
    later_notes: list = field(default_factory=list)  # (note, added_at, moderator_id); the only permitted change

    def add_later_note(self, note: str, added_at: datetime, moderator_id: int) -> None:
        self.later_notes.append((note, added_at, moderator_id))
