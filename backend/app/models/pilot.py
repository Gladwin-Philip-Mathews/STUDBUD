"""OnboardingAnswer, AcceptedDomain and the pilot report rows (CD-1b)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

ANSWERS = ("0", "1 to 2", "3 to 5", "more than 5", "skipped")  # DR-012
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
