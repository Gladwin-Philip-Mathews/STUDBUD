"""OnboardingAnswer, AcceptedDomain and the pilot report rows (CD-1b)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import ContactRange

ANSWERS = tuple(a.value for a in ContactRange)  # DR-012
WEEKS = (1, 12)


@dataclass
class OnboardingAnswer:
    account_id: Optional[int]
    week: int
    answer: str
    cohort: str
    answered_at: datetime
    id: Optional[int] = None


@dataclass
class AcceptedDomain:
    domain: str
    added_at: Optional[datetime] = None
    added_by: Optional[int] = None


@dataclass(frozen=True)
class SystemSetting:
    """CD-1a SystemSetting {name in the NFR-012 list}: one configurable limit and when it was last changed (DR-014)."""
    name: str
    value: int
    unit: str = "count"
    changed_at: Optional[datetime] = None
    changed_by: Optional[int] = None

    def as_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "unit": self.unit,
                "changedAt": self.changed_at.isoformat() if self.changed_at else None}


@dataclass(frozen=True)
class AuditRecord:
    """CD-1a AuditRecord {readOnly}: who did what to which item, and when (DR-015, NFR-015)."""
    at: datetime
    actor_id: Optional[int]
    action: str
    item_ref: str = ""
    detail: str = ""
    id: Optional[int] = None

    def __getitem__(self, key):  # the earlier tests read entries as dictionaries; both forms work
        return getattr(self, key)


@dataclass
class CohortRow:
    """One cohort group of the pilot report. Contains numbers only, never a name (FR-094)."""
    cohort: str
    students: int
    requests_sent: int = 0
    accepted_within_7_days_pct: Optional[float] = None
    week1_answers: dict = field(default_factory=dict)
    week12_answers: dict = field(default_factory=dict)
    answered_both: int = 0
    contact_increased: int = 0
    safety_reports: int = 0
    acknowledged_within_48h_pct: Optional[float] = None
    upheld_reports: int = 0
    active_users: int = 0
    upheld_per_100_active: Optional[float] = None
