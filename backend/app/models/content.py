"""Community, Post and Reply (CD-1b). Post and Reply realize Reportable (DD-06)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

EDIT_WINDOW = timedelta(minutes=15)  # FR-033


class Reportable(ABC):
    """Anything a safety report can name: a post, a reply or a message (DD-06)."""

    @abstractmethod
    def author(self) -> int:
        """The id of the account that wrote it."""

    @abstractmethod
    def hide(self) -> None:
        """Set the status to hidden (FR-065). The author still sees it with a notice."""


@dataclass
class Community:
    name: str
    kind: str  # course | interest (CommunityKind)
    course_code: Optional[str] = None
    status: str = "active"
    member_count: int = 0
    created_at: Optional[datetime] = None  # D4, CD-1a createdAt
    id: Optional[int] = None

    def is_active(self) -> bool:
        return self.status == "active"


@dataclass
class Post(Reportable):
    community_id: int
    author_id: int
    kind: str
    title: str
    body: str
    created_at: datetime
    status: str = "visible"
    edited_at: Optional[datetime] = None
    id: Optional[int] = None

    def author(self) -> int:
        return self.author_id

    def hide(self) -> None:
        self.status = "hidden"

    def can_edit(self, now: datetime) -> bool:
        return self.status == "visible" and now - self.created_at <= EDIT_WINDOW


@dataclass
class Reply(Reportable):
    post_id: int
    author_id: int
    body: str
    created_at: datetime
    status: str = "visible"
    edited_at: Optional[datetime] = None
    id: Optional[int] = None

    def author(self) -> int:
        return self.author_id

    def hide(self) -> None:
        self.status = "hidden"

    def can_edit(self, now: datetime) -> bool:
        return self.status == "visible" and now - self.created_at <= EDIT_WINDOW


@dataclass
class Message(Reportable):
    connection_id: int
    sender_id: int
    body: str
    sent_at: datetime
    status: str = "visible"  # visible | hidden (DR-008)
    read_at: Optional[datetime] = None
    id: Optional[int] = None

    def author(self) -> int:
        return self.sender_id

    def hide(self) -> None:
        self.status = "hidden"
