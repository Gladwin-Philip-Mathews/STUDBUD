"""Entity classes from CD-1a (M3 Section 3). Rules that need other objects live in services."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .enums import AccountStatus, ConnectionStatus, EmailStatus, EventType, Role

MAX_EMAIL_RESENDS = 3  # CH-15: emailResends is {0..3}


@dataclass
class Account:
    email: str
    display_name: str
    password_hash: str
    status: AccountStatus = AccountStatus.UNVERIFIED
    role: Role = Role.STUDENT
    failed_sign_ins: int = 0
    first_failed_at: Optional[datetime] = None
    locked_until: Optional[datetime] = None
    last_sign_in_at: Optional[datetime] = None
    email_notifications: bool = True
    created_at: Optional[datetime] = None
    id: Optional[int] = None

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and now < self.locked_until

    def can_sign_in(self, now: datetime) -> bool:
        """FR-008/FR-009: verified, not suspended, not locked out."""
        return self.status == AccountStatus.VERIFIED and not self.is_locked(now)

    def record_failed_sign_in(self, now: datetime, attempts: int, window_min: int, lock_min: int) -> None:
        """Lock the account after `attempts` failures inside `window_min` minutes (NFR-012)."""
        window = timedelta(minutes=window_min)
        if self.first_failed_at is None or now - self.first_failed_at > window:
            self.first_failed_at = now
            self.failed_sign_ins = 0
        self.failed_sign_ins += 1
        if self.failed_sign_ins >= attempts:
            self.locked_until = now + timedelta(minutes=lock_min)
            self.failed_sign_ins = 0
            self.first_failed_at = None

    def record_successful_sign_in(self, now: datetime) -> None:
        self.failed_sign_ins = 0
        self.first_failed_at = None
        self.locked_until = None
        self.last_sign_in_at = now

    def suspend(self) -> None:
        self.status = AccountStatus.SUSPENDED


@dataclass
class VerificationToken:
    account_id: int
    token_hash: str
    expires_at: datetime
    created_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    is_resend: bool = False
    id: Optional[int] = None

    def is_valid(self, now: datetime) -> bool:
        return self.used_at is None and now < self.expires_at


@dataclass
class Profile:
    account_id: int
    intent: str = "both"  # friendship | study partner | both
    cohort: str = "prefer not to say"
    year_of_study: Optional[int] = None
    interests: list = field(default_factory=list)  # up to 20 (DR-002)
    course_codes: list = field(default_factory=list)

    def shared_items_with(self, other: "Profile") -> int:
        """Count shared courses and interests, used to order suggestions (FR-040)."""
        return len(set(self.course_codes) & set(other.course_codes)) + len(
            {i.lower() for i in self.interests} & {i.lower() for i in other.interests}
        )


@dataclass
class Course:
    code: str
    name: str
    status: str = "active"
    id: Optional[int] = None


@dataclass
class Connection:
    requester_id: Optional[int]
    receiver_id: Optional[int]
    status: ConnectionStatus = ConnectionStatus.PENDING
    note: str = ""
    created_at: Optional[datetime] = None
    status_changed_at: Optional[datetime] = None
    id: Optional[int] = None

    def is_open(self) -> bool:
        return self.status in (ConnectionStatus.PENDING, ConnectionStatus.ACCEPTED)

    def _set(self, status: ConnectionStatus, now: datetime) -> None:
        self.status = status
        self.status_changed_at = now

    def accept(self, now): self._set(ConnectionStatus.ACCEPTED, now)
    def decline(self, now): self._set(ConnectionStatus.DECLINED, now)
    def withdraw(self, now): self._set(ConnectionStatus.WITHDRAWN, now)
    def remove(self, now): self._set(ConnectionStatus.REMOVED, now)


@dataclass
class Notification:
    recipient_id: int
    event_type: EventType
    body: str
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    email_status: EmailStatus = EmailStatus.NOT_SENT
    email_resends: int = 0
    id: Optional[int] = None

    def can_resend(self) -> bool:
        return self.email_resends < MAX_EMAIL_RESENDS
