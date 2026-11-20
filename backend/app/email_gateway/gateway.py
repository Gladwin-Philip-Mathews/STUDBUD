"""EmailGateway (DD-03, CD-1b «gateway»): the only route to email. Live and stub are swapped by setting (CON-009).

send() returns a HandoffResult (CD-1b): HANDED_OVER when the mail route accepted the message, UNAVAILABLE when it
could not be reached. Whether a handed-over message is later *returned* is a delivery status (DF-29) that the route
reports through NotificationService.onDeliveryStatus(), not something the gateway decides.
"""
from abc import ABC, abstractmethod
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from typing import Optional

from ..models.enums import HandoffResult


def tls_context() -> ssl.SSLContext:
    """NFR-010: the server-to-email-service leg uses TLS 1.2 or later; older versions are refused."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


@dataclass(frozen=True)
class EmailMessage:
    """CD-1b «datatype» EmailMessage {to, subject, body, notificationId}. The body names the event and a display
    name only; never message text or report details (FR-081). notification_id is the message reference the mail
    route quotes in its delivery status (DF-29); it is None for a verification email, which has no notification."""
    to: str
    subject: str
    body: str
    notification_id: Optional[int] = None


class EmailGateway(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> HandoffResult:
        """Hand the message to the mail route (DF-28). HANDED_OVER or UNAVAILABLE; never raises."""


class StubEmailGateway(EmailGateway):
    """Keeps sent messages for tests (CD-1b sentMessages()). Set `available = False` to simulate an outage."""

    def __init__(self, echo: bool = False):
        self.echo = echo  # print each message to the backend console (development only)
        self.sent: list = []
        self.attempts = 0
        self.available = True

    def send(self, message: EmailMessage) -> HandoffResult:
        self.attempts += 1
        if not self.available:
            return HandoffResult.UNAVAILABLE
        self.sent.append(message)
        if self.echo:
            print(f"\n[email stub] to={message.to} | {message.subject}\n    {message.body}\n", flush=True)
        return HandoffResult.HANDED_OVER

    def sent_messages(self) -> list:
        """CD-1b StubEmailGateway.sentMessages(): every message handed over so far, in order."""
        return list(self.sent)


class RitEmailGateway(EmailGateway):
    """Live route to the RIT Email Service (IF-003, CON-009), over SMTP with TLS 1.2 or later (NFR-010)."""

    def __init__(self, host: str, port: int = 587, sender: str = "", username: str = "", password: str = "",
                 timeout: float = 10.0):
        self.host, self.port, self.sender = host, port, sender
        self.username, self.password, self.timeout = username, password, timeout

    def send(self, message: EmailMessage) -> HandoffResult:
        mime = MimeMessage()
        mime["From"], mime["To"], mime["Subject"] = self.sender, message.to, message.subject
        if message.notification_id is not None:
            mime["X-StudBud-Notification"] = str(message.notification_id)  # the reference quoted in DF-29
        mime.set_content(message.body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.starttls(context=tls_context())
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(mime)
            return HandoffResult.HANDED_OVER
        except (OSError, smtplib.SMTPException):
            return HandoffResult.UNAVAILABLE  # the in-app notification and the connection are unaffected (SD-1 M30, M31)


def build_gateway(config: dict, echo: bool = False) -> EmailGateway:
    """Chooses the live or stub gateway from settings (CON-009). Live needs SMTP_HOST; otherwise the stub is used."""
    if config.get("EMAIL_MODE") == "live" and config.get("SMTP_HOST"):
        return RitEmailGateway(config["SMTP_HOST"], int(config.get("SMTP_PORT") or 587), config.get("SMTP_SENDER", ""),
                               config.get("SMTP_USER", ""), config.get("SMTP_PASSWORD", ""))
    return StubEmailGateway(echo=echo)
