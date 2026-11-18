"""EmailGateway (DD-03): the only route to email. Live and stub are swapped by setting (CON-009)."""
from abc import ABC, abstractmethod
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str  # names the event and a display name only (FR-081)


class EmailGateway(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> bool:
        """Hand the message to the mail route. True = handed over, False = returned/unavailable."""


class StubEmailGateway(EmailGateway):
    """Keeps sent messages for tests. Set `available = False` to simulate an outage."""

    def __init__(self, echo: bool = False):
        self.echo = echo  # print each message to the backend console (development only)
        self.sent: list = []
        self.attempts = 0
        self.available = True

    def send(self, message: EmailMessage) -> bool:
        self.attempts += 1
        if not self.available:
            return False
        self.sent.append(message)
        if self.echo:
            print(f"\n[email stub] to={message.to} | {message.subject}\n    {message.body}\n", flush=True)
        return True


class RitEmailGateway(EmailGateway):
    """Live route to the RIT Email Service (IF-003, CON-009), over SMTP. Any failure means "returned"."""

    def __init__(self, host: str, port: int = 587, sender: str = "", username: str = "", password: str = "",
                 timeout: float = 10.0):
        self.host, self.port, self.sender = host, port, sender
        self.username, self.password, self.timeout = username, password, timeout

    def send(self, message: EmailMessage) -> bool:
        mime = MimeMessage()
        mime["From"], mime["To"], mime["Subject"] = self.sender, message.to, message.subject
        mime.set_content(message.body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(mime)
            return True
        except (OSError, smtplib.SMTPException):
            return False  # the in-app notification and the connection are unaffected (SD-1 M30, M31)


def build_gateway(config: dict, echo: bool = False) -> EmailGateway:
    """Chooses the live or stub gateway from settings (CON-009). Live needs SMTP_HOST; otherwise the stub is used."""
    if config.get("EMAIL_MODE") == "live" and config.get("SMTP_HOST"):
        return RitEmailGateway(config["SMTP_HOST"], int(config.get("SMTP_PORT") or 587), config.get("SMTP_SENDER", ""),
                               config.get("SMTP_USER", ""), config.get("SMTP_PASSWORD", ""))
    return StubEmailGateway(echo=echo)
