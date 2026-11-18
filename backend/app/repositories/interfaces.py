"""Repository interfaces (DD-10): services depend on these, never on SQLite directly."""
from abc import ABC, abstractmethod
from typing import Optional


class AccountRepository(ABC):
    @abstractmethod
    def add(self, account): ...
    @abstractmethod
    def get(self, account_id: int): ...
    @abstractmethod
    def find_by_email(self, email: str): ...
    @abstractmethod
    def display_name_taken(self, display_name: str) -> bool: ...
    @abstractmethod
    def save(self, account): ...
    @abstractmethod
    def with_role(self, role) -> list: ...
    @abstractmethod
    def erase(self, account_id: int) -> None:
        """Delete credentials and identity but keep the row, so content shows as "deleted student" (FR-015)."""
    @abstractmethod
    def domain_accepted(self, email: str) -> bool: ...


class VerificationTokenRepository(ABC):
    @abstractmethod
    def add(self, token): ...
    @abstractmethod
    def find_by_hash(self, token_hash: str): ...
    @abstractmethod
    def save(self, token): ...
    @abstractmethod
    def count_resends_since(self, account_id: int, since) -> int: ...
    @abstractmethod
    def invalidate_all(self, account_id: int, now) -> None: ...


class ProfileRepository(ABC):
    @abstractmethod
    def get(self, account_id: int): ...
    @abstractmethod
    def save(self, profile): ...
    @abstractmethod
    def delete(self, account_id: int) -> None:
        """Remove profile, interests, courses and dismissed suggestions of an account (FR-015)."""
    @abstractmethod
    def candidates(self, exclude_id: int) -> list:
        """(Account, Profile) pairs for verified students other than exclude_id."""


class ConnectionRepository(ABC):
    @abstractmethod
    def add(self, connection): ...
    @abstractmethod
    def get(self, connection_id: int): ...
    @abstractmethod
    def between(self, a_id: int, b_id: int) -> list: ...
    @abstractmethod
    def find_open_between(self, a_id: int, b_id: int):
        """CD-1a findOpenBetween(): the pending or accepted connection between two accounts, either direction, or None."""
    @abstractmethod
    def last_decline_by(self, receiver_id: int, sender_id: int):
        """CD-1a lastDeclineBy(): when the receiver last declined the sender, or None."""
    @abstractmethod
    def for_account(self, account_id: int) -> list: ...
    @abstractmethod
    def save(self, connection): ...
    @abstractmethod
    def dismiss(self, account_id: int, dismissed_id: int) -> None: ...
    @abstractmethod
    def archive_timings(self, account_id: int) -> None:
        """Keep each request's timing and outcome without identities before the account's requests are deleted (FR-091)."""
    @abstractmethod
    def delete_for_account(self, account_id: int) -> None:
        """Remove every connection the account is part of (FR-015)."""
    @abstractmethod
    def dismissed_ids(self, account_id: int) -> set: ...


class NotificationRepository(ABC):
    @abstractmethod
    def add(self, notification): ...
    @abstractmethod
    def get(self, notification_id: int): ...
    @abstractmethod
    def for_recipient(self, account_id: int) -> list: ...
    @abstractmethod
    def save(self, notification): ...
    @abstractmethod
    def delete_for_recipient(self, account_id: int) -> None:
        """Remove all notifications of an account (FR-015)."""
    @abstractmethod
    def pending_email(self) -> list: ...
    @abstractmethod
    def mark_all_read(self, account_id: int, now) -> None: ...


class CourseRepository(ABC):
    @abstractmethod
    def add(self, course): ...
    @abstractmethod
    def find_by_code(self, code: str): ...
    @abstractmethod
    def all(self) -> list: ...
    @abstractmethod
    def active_matching(self, query: str) -> list:
        """Active courses whose code or name contains the query (FR-011)."""
    @abstractmethod
    def save(self, course): ...
