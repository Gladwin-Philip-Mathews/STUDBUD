"""ConnectionService (process 4.0): suggestions, sending and answering requests (SD-1).

FR-040 to FR-048, FR-091. checkRequest applies the refusal rules in the fixed order of SD-1.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from ..container import service
from ..models import AccountStatus, Connection, ConnectionStatus
from ..models.enums import EventType, RefusalReason, SettingName

MAX_NOTE = 200
MAX_SUGGESTIONS = 10


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RequestResult:
    """Exactly one of connection or refusal (M3 RequestResult)."""
    connection: Optional[Connection] = None
    refusal: Optional[RefusalReason] = None


@dataclass
class Suggestion:
    account_id: int
    display_name: str
    intent: str
    shared_courses: list
    shared_interests: list

    @property
    def shared_count(self) -> int:
        return len(self.shared_courses) + len(self.shared_interests)


class ConnectionService:
    def __init__(self, accounts, profiles, connections, settings, notifications,
                 clock: Callable[[], datetime] = utc_now):
        self.accounts, self.profiles, self.connections = accounts, profiles, connections
        self.settings, self.notifications, self.clock = settings, notifications, clock

    # ---- SD-1: refusal rules in a fixed order (M14, M15) ----
    def check_request(self, sender_id: int, receiver_id: int, note: str) -> Optional[RefusalReason]:
        if len(note or "") > MAX_NOTE:
            return RefusalReason.NOTE_TOO_LONG
        if sender_id == receiver_id:
            return RefusalReason.SELF
        receiver = self.accounts.get(receiver_id)
        if receiver is None or receiver.status != AccountStatus.VERIFIED:
            return RefusalReason.NOT_AVAILABLE  # missing, unverified or suspended (FR-043)
        open_connection = self.connections.find_open_between(sender_id, receiver_id)  # M6 to M9
        if open_connection is not None and open_connection.status == ConnectionStatus.ACCEPTED:
            return RefusalReason.ALREADY_CONNECTED
        if open_connection is not None:
            return RefusalReason.PENDING_EXISTS
        declined_at = self.connections.last_decline_by(receiver_id, sender_id)  # M10, M11
        wait = self.settings.duration(SettingName.REQUEST_DECLINE_WAIT)  # M12, M13
        if declined_at is not None and self.clock() - declined_at < wait:
            return RefusalReason.RECENTLY_DECLINED
        return None

    def send_request(self, sender_id: int, receiver_id: int, note: str = "") -> RequestResult:
        refusal = self.check_request(sender_id, receiver_id, note)
        if refusal:
            return RequestResult(refusal=refusal)
        now = self.clock()
        c = self.connections.add(Connection(sender_id, receiver_id, note=note or "", created_at=now,
                                            status_changed_at=now))
        sender = self.accounts.get(sender_id)
        self.notifications.notify(receiver_id, EventType.REQUEST_RECEIVED,
                                  f"{sender.display_name} sent you a connection request.")
        return RequestResult(connection=c)

    # ---- answering (FR-044 to FR-046, FR-048) ----
    def respond(self, connection_id: int, actor_id: int, accept: bool) -> Optional[Connection]:
        """CD-1a ConnectionService.respond(): the receiver answers a pending request."""
        return self.accept(connection_id, actor_id) if accept else self.decline(connection_id, actor_id)

    def _pending_for_receiver(self, connection_id, actor_id) -> Optional[Connection]:
        c = self.connections.get(connection_id)
        if c and c.status == ConnectionStatus.PENDING and c.receiver_id == actor_id:
            return c
        return None

    def accept(self, connection_id: int, actor_id: int) -> Optional[Connection]:
        c = self._pending_for_receiver(connection_id, actor_id)
        if c is None:
            return None
        c.accept(self.clock())
        self.connections.save(c)
        me = self.accounts.get(actor_id)
        self.notifications.notify(c.requester_id, EventType.REQUEST_ANSWERED,
                                  f"{me.display_name} accepted your connection request.")
        return c

    def decline(self, connection_id: int, actor_id: int) -> Optional[Connection]:
        c = self._pending_for_receiver(connection_id, actor_id)
        if c is None:
            return None
        c.decline(self.clock())
        self.connections.save(c)
        # FR-045: tell the requester only that the request was not accepted
        self.notifications.notify(c.requester_id, EventType.REQUEST_ANSWERED, "Your connection request was not accepted.")
        return c

    def withdraw(self, connection_id: int, actor_id: int) -> Optional[Connection]:
        c = self.connections.get(connection_id)
        if c is None or c.status != ConnectionStatus.PENDING or c.requester_id != actor_id:
            return None
        c.withdraw(self.clock())
        self.connections.save(c)
        return c

    def remove(self, connection_id: int, actor_id: int) -> Optional[Connection]:
        c = self.connections.get(connection_id)
        if c is None or c.status != ConnectionStatus.ACCEPTED or actor_id not in (c.requester_id, c.receiver_id):
            return None
        c.remove(self.clock())
        self.connections.save(c)
        return c

    # ---- lists (FR-047) ----
    def _other(self, c: Connection, me: int) -> int:
        return c.receiver_id if c.requester_id == me else c.requester_id

    def accepted_for(self, account_id: int) -> list:
        mine = self.profiles.get(account_id)
        out = []
        for c in self.connections.for_account(account_id):
            if c.status != ConnectionStatus.ACCEPTED:
                continue
            other_id = self._other(c, account_id)
            other = self.accounts.get(other_id)
            their = self.profiles.get(other_id)
            if other is None:
                continue
            out.append({
                "connectionId": c.id, "accountId": other_id, "displayName": other.display_name,
                "sharedCourses": sorted(set(mine.course_codes) & set(their.course_codes)) if mine and their else [],
                "sharedInterests": sorted({i.lower() for i in mine.interests} & {i.lower() for i in their.interests})
                if mine and their else [],
            })
        return out

    def incoming(self, account_id: int) -> list:
        return [(c, self.accounts.get(c.requester_id)) for c in self.connections.for_account(account_id)
                if c.status == ConnectionStatus.PENDING and c.receiver_id == account_id]

    def outgoing(self, account_id: int) -> list:
        return [(c, self.accounts.get(c.receiver_id)) for c in self.connections.for_account(account_id)
                if c.status == ConnectionStatus.PENDING and c.requester_id == account_id]

    # ---- suggestions (FR-040, FR-041) ----
    def suggestions(self, account_id: int) -> list:
        mine = self.profiles.get(account_id)
        if mine is None:
            return []
        dismissed = self.connections.dismissed_ids(account_id)
        blocked = set()
        for c in self.connections.for_account(account_id):
            other = self._other(c, account_id)
            if c.status in (ConnectionStatus.PENDING, ConnectionStatus.ACCEPTED):
                blocked.add(other)
            elif c.status == ConnectionStatus.DECLINED and c.receiver_id == other:
                blocked.add(other)  # students who declined the viewer are excluded without saying why
        results = []
        my_interests = {i.lower() for i in mine.interests}
        for account, theirs in self.profiles.candidates(account_id):
            if account.id in dismissed or account.id in blocked:
                continue
            if theirs.intent != mine.intent and theirs.intent != "both":  # FR-040
                continue
            courses = sorted(set(mine.course_codes) & set(theirs.course_codes))
            interests = sorted(my_interests & {i.lower() for i in theirs.interests})
            if not courses and not interests:
                continue
            results.append(Suggestion(account.id, account.display_name, theirs.intent, courses, interests))
        results.sort(key=lambda s: (-s.shared_count, s.display_name.lower()))
        return results[:MAX_SUGGESTIONS]

    def dismiss_suggestion(self, account_id: int, dismissed_id: int) -> None:
        self.connections.dismiss(account_id, dismissed_id)


@service("connections")
def build_connection_service(d):
    from ..container import get_service
    kwargs = {"clock": d.clock} if d.clock else {}
    return ConnectionService(d.accounts, d.profiles, d.connections, d.settings, get_service("notifications"), **kwargs)
