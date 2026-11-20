"""MessagingService (process 5.0): private messages between accepted connections only.

FR-050 to FR-052, DR-008, OR-001. The email for a new message never carries its text (FR-081).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from ..container import service
from ..models import ConnectionStatus, EventType, ItemRef, Message
from ..models.enums import SettingName

MAX_LENGTH = 1000


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SendResult:
    message: Optional[Message] = None
    error: Optional[str] = None  # not_allowed | invalid


@dataclass
class Conversation:
    connection_id: int
    other_id: int
    other_name: str
    last_at: Optional[datetime]
    unread: int
    messages: list = field(default_factory=list)


class MessagingService:
    def __init__(self, accounts, connections, messages, settings, notifications,
                 clock: Callable[[], datetime] = utc_now):
        self.accounts, self.connections, self.messages = accounts, connections, messages
        self.settings, self.notifications, self.clock = settings, notifications, clock

    def _accepted(self, connection_id: int, account_id: int):
        """FR-051: the connection must be accepted and include the account. Anything else gets the same answer."""
        c = self.connections.get(connection_id)
        if c is None or c.status != ConnectionStatus.ACCEPTED or account_id not in (c.requester_id, c.receiver_id):
            return None
        return c

    def send(self, sender_id: int, connection_id: int, text) -> SendResult:
        c = self._accepted(connection_id, sender_id)
        if c is None:
            return SendResult(error="not_allowed")
        text = (text or "").strip()
        if not 1 <= len(text) <= MAX_LENGTH:
            return SendResult(error="invalid")
        m = self.messages.add(Message(connection_id, sender_id, text, sent_at=self.clock()))
        receiver_id = c.receiver_id if c.requester_id == sender_id else c.requester_id
        me = self.accounts.get(sender_id)
        self.notifications.notify(receiver_id, EventType.MESSAGE_RECEIVED, f"{me.display_name} sent you a message.",
                                  ItemRef("conversation", connection_id))  # DF-18
        return SendResult(message=m)

    def conversations(self, account_id: int) -> list:
        """FR-052: most recent first, with an unread count. Accepted connections without messages come last."""
        result = []
        for c in self.connections.for_account(account_id):
            if c.status != ConnectionStatus.ACCEPTED:
                continue
            other_id = c.receiver_id if c.requester_id == account_id else c.requester_id
            other = self.accounts.get(other_id)
            result.append(Conversation(c.id, other_id, other.display_name, self.messages.last_sent_at(c.id),
                                       self.messages.unread_count(c.id, account_id)))
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        result.sort(key=lambda x: (x.last_at or epoch, x.connection_id), reverse=True)
        return result

    def open(self, account_id: int, connection_id: int) -> Optional[Conversation]:
        """Messages in time order. Opening clears the unread count. A hidden message shows only to its sender."""
        c = self._accepted(connection_id, account_id)
        if c is None:
            return None
        self.messages.mark_read(connection_id, account_id, self.clock())
        other_id = c.receiver_id if c.requester_id == account_id else c.requester_id
        shown = [m for m in self.messages.for_connection(connection_id)
                 if m.status == "visible" or m.sender_id == account_id]
        return Conversation(connection_id, other_id, self.accounts.get(other_id).display_name,
                            self.messages.last_sent_at(connection_id), 0, shown)

    def apply_retention(self, keep_ids=frozenset()) -> int:
        """OR-001: delete messages older than the retention setting, except those attached to an open or recent report."""
        cutoff = self.clock() - self.settings.duration(SettingName.MESSAGE_RETENTION)
        return self.messages.purge_before(cutoff, set(keep_ids))


@service("messaging")
def build_messaging_service(d):
    from ..container import get_service
    kwargs = {"clock": d.clock} if d.clock else {}
    return MessagingService(d.accounts, d.connections, d.messages, d.settings, get_service("notifications"), **kwargs)
