"""Enumerations fixed by the M2 SRS and M3 design (Section 3.2)."""
from enum import Enum


class AccountStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Role(str, Enum):
    STUDENT = "student"
    MODERATOR = "moderator"
    ADMINISTRATOR = "administrator"


class ConnectionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    REMOVED = "removed"


class RefusalReason(str, Enum):
    NOTE_TOO_LONG = "NOTE_TOO_LONG"
    SELF = "SELF"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    ALREADY_CONNECTED = "ALREADY_CONNECTED"
    PENDING_EXISTS = "PENDING_EXISTS"
    RECENTLY_DECLINED = "RECENTLY_DECLINED"


class EventType(str, Enum):
    REPLY_ADDED = "REPLY_ADDED"
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REQUEST_ANSWERED = "REQUEST_ANSWERED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    REPORT_ACKNOWLEDGED = "REPORT_ACKNOWLEDGED"
    REPORT_CLOSED = "REPORT_CLOSED"


class EmailStatus(str, Enum):
    NOT_SENT = "not sent"
    HANDED_OVER = "handed over"
    RETURNED = "returned"


class HandoffResult(str, Enum):
    """CD-1b EmailGateway.send() result. HANDED_OVER: the mail route accepted the message (SD-1 M27 to M29).
    UNAVAILABLE: the route could not be reached; the email status stays "not sent" and the handoff is retried
    (SD-1 M30, M31). A message the route later reports back as undelivered is a *delivery status* (DF-29,
    EmailStatus.RETURNED), which is what FR-084 limits to three resends."""
    HANDED_OVER = "handed over"
    UNAVAILABLE = "unavailable"

    def __bool__(self) -> bool:  # `if gateway.send(message):` reads as "was it handed over"
        return self is HandoffResult.HANDED_OVER


class SettingName(str, Enum):
    VERIFICATION_LINK_LIFE = "VERIFICATION_LINK_LIFE"  # hours
    RESEND_LIMIT = "RESEND_LIMIT"  # per hour
    LOCKOUT_ATTEMPTS = "LOCKOUT_ATTEMPTS"
    LOCKOUT_WINDOW = "LOCKOUT_WINDOW"  # minutes
    LOCKOUT_PERIOD = "LOCKOUT_PERIOD"  # minutes
    OVERDUE_FLAG = "OVERDUE_FLAG"  # hours
    REQUEST_DECLINE_WAIT = "REQUEST_DECLINE_WAIT"  # days
    SESSION_IDLE_TIME = "SESSION_IDLE_TIME"  # hours
    MESSAGE_RETENTION = "MESSAGE_RETENTION"  # days (CH-15)
    LOG_RETENTION = "LOG_RETENTION"  # days (CH-15)


class ConnectionIntent(str, Enum):  # DR-002
    FRIENDSHIP = "friendship"
    STUDY_PARTNER = "study partner"
    BOTH = "both"


class Cohort(str, Enum):  # DR-002: used only for pilot reporting, never shown to students (FR-014)
    FIRST_YEAR = "first year"
    INTERNATIONAL = "international"
    BOTH = "both"
    NEITHER = "neither"
    PREFER_NOT_TO_SAY = "prefer not to say"


class RecordStatus(str, Enum):  # DR-003
    ACTIVE = "active"
    ARCHIVED = "archived"


class CommunityKind(str, Enum):  # DR-004
    COURSE = "course"
    INTEREST = "interest"


class PostKind(str, Enum):  # DR-005
    QUESTION = "question"
    SHARE = "share"
    STUDY_PARTNER_REQUEST = "study partner request"


class ContentStatus(str, Enum):  # DR-005, DR-006, DR-008 (Message uses visible and hidden only)
    VISIBLE = "visible"
    HIDDEN = "hidden"
    DELETED = "deleted"


class ContactRange(str, Enum):  # DR-012: the onboarding answer of FR-090
    NONE = "0"
    ONE_TO_TWO = "1 to 2"
    THREE_TO_FIVE = "3 to 5"
    MORE_THAN_FIVE = "more than 5"
    SKIPPED = "skipped"


class ReportReason(str, Enum):  # DR-009
    HARASSMENT = "harassment"
    SPAM = "spam"
    UNSAFE = "unsafe or inappropriate content"
    ACADEMIC_INTEGRITY = "academic integrity"
    OTHER = "other"


class ReportStatus(str, Enum):  # DR-009
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CLOSED = "closed"


class Decision(str, Enum):  # DR-010
    UPHELD = "upheld"
    DISMISSED = "dismissed"


class ConductAction(str, Enum):  # DR-010
    NONE = "none"
    WARNING = "warning"
    CONTENT_HIDDEN = "content hidden"
    ACCOUNT_SUSPENDED = "account suspended"
