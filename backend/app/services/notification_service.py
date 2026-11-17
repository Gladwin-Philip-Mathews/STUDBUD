"""NotificationService (process 7.0): in-app notifications, email after the response, resend limit.

FR-080 to FR-084, NFR-004. The email goes only through EmailGateway (DD-03) and never carries
message text or report details (FR-081).
"""
from datetime import datetime, timezone
from typing import Callable, Optional

from ..container import service
from ..email_gateway import EmailGateway, EmailMessage
from ..models import Notification
from ..models.entities import MAX_EMAIL_RESENDS
from ..models.enums import EmailStatus, EventType

SUBJECTS = {
    EventType.REPLY_ADDED: "New reply to your post",
    EventType.REQUEST_RECEIVED: "New connection request",
    EventType.REQUEST_ANSWERED: "Update on your connection request",
    EventType.MESSAGE_RECEIVED: "New message",
    EventType.REPORT_ACKNOWLEDGED: "Your report was received",
    EventType.REPORT_CLOSED: "Your report was closed",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationService:
    def __init__(self, notifications, accounts, gateway: EmailGateway, clock: Callable[[], datetime] = utc_now,
                 on_email_pending: Optional[Callable[[], None]] = None):
        self.notifications, self.accounts, self.gateway = notifications, accounts, gateway
        self.clock, self.on_email_pending = clock, on_email_pending

    def create(self, recipient_id: int, event: EventType, body: str) -> Notification:
        """Always creates the in-app notification. The email is handed over later, after the response (DD-04)."""
        n = self.notifications.add(Notification(recipient_id, event, body, created_at=self.clock()))
        if self.on_email_pending:
            self.on_email_pending()
        return n

    # ---- email, run after the response has been sent ----
    def dispatch_pending(self) -> int:
        """Hand over each unsent or returned email. At most 3 resends, so at most 4 handoffs (CH-15, AC-FR-084a)."""
        handed = 0
        for n in self.notifications.pending_email():
            account = self.accounts.get(n.recipient_id)
            if account is None or not account.email_notifications:
                continue  # FR-082: email switched off, in-app notification stays
            is_resend = n.email_status == EmailStatus.RETURNED
            if is_resend:
                if not n.can_resend():
                    continue
                n.email_resends += 1
            ok = self.gateway.send(EmailMessage(account.email, SUBJECTS[n.event_type], n.body))
            n.email_status = EmailStatus.HANDED_OVER if ok else EmailStatus.RETURNED
            self.notifications.save(n)
            handed += ok
        return handed

    # ---- in-app list (FR-083) ----
    def list_for(self, account_id: int) -> list:
        return self.notifications.for_recipient(account_id)

    def unread_count(self, account_id: int) -> int:
        return sum(1 for n in self.notifications.for_recipient(account_id) if n.read_at is None)

    def mark_read(self, notification_id: int, account_id: int) -> bool:
        n = self.notifications.get(notification_id)
        if n is None or n.recipient_id != account_id:
            return False
        if n.read_at is None:
            n.read_at = self.clock()
            self.notifications.save(n)
        return True

    def mark_all_read(self, account_id: int) -> None:
        self.notifications.mark_all_read(account_id, self.clock())

    # ---- settings (FR-082) ----
    def set_email_enabled(self, account_id: int, enabled: bool) -> None:
        account = self.accounts.get(account_id)
        account.email_notifications = bool(enabled)
        self.accounts.save(account)


@service("notifications")
def build_notification_service(d):
    kwargs = {"clock": d.clock} if d.clock else {}
    return NotificationService(d.notifications, d.accounts, d.gateway, on_email_pending=d.on_email_pending, **kwargs)
