"""EmailGateway (DD-03): the only route to email. Live and stub are swapped by setting (CON-009)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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
