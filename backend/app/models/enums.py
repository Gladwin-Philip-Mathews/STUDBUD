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
