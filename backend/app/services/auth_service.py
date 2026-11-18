"""AuthService (process 1.0): registration, verification, sign-in, lock-out, session check.

FR-001 to FR-009, NFR-009 (no clear-text passwords or tokens), NFR-011, NFR-013.
"""
import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from ..container import service
from ..email_gateway import EmailGateway, EmailMessage
from ..models import Account, AccountStatus, VerificationToken
from ..models.enums import SettingName

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SignInOutcome(str, Enum):
    OK = "ok"
    INVALID = "invalid"  # wrong password or unknown email, same message (FR-008)
    LOCKED = "locked"  # FR-009
    UNVERIFIED = "unverified"  # FR-007
    SUSPENDED = "suspended"  # FR-066


class ResendOutcome(str, Enum):
    SENT = "sent"
    LIMIT = "limit"  # FR-006: 3 per hour


@dataclass
class RegistrationResult:
    ok: bool
    field_errors: dict = field(default_factory=dict)
    rejected_domain: bool = False


@dataclass
class SignInResult:
    outcome: SignInOutcome
    account: Optional[Account] = None


class AuthService:
    def __init__(self, accounts, tokens, settings, gateway: EmailGateway, base_url: str,
                 clock: Callable[[], datetime] = utc_now, hash_method: str = "pbkdf2:sha256"):
        self.accounts, self.tokens, self.settings = accounts, tokens, settings
        self.gateway, self.base_url, self.clock = gateway, base_url.rstrip("/"), clock
        self.hash_method = hash_method

    # ---- registration (FR-001 to FR-004) ----
    def register(self, email: str, display_name: str, password: str, accepted_notice: bool = False) -> RegistrationResult:
        email = (email or "").strip().lower()
        display_name = (display_name or "").strip()
        errors = {}
        if not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
        elif not self.accounts.domain_accepted(email):
            return RegistrationResult(False, {"email": "Only RIT email addresses are accepted."}, rejected_domain=True)
        if len(password or "") < 8 or not re.search(r"[A-Za-z]", password or "") or not re.search(r"\d", password or ""):
            errors["password"] = "Use at least 8 characters with a letter and a digit."
        if not 3 <= len(display_name) <= 30:
            errors["displayName"] = "Display name must be 3 to 30 characters."
        elif self.accounts.display_name_taken(display_name):
            existing = self.accounts.find_by_email(email) if "email" not in errors else None
            if existing is None or existing.display_name.lower() != display_name.lower():
                errors["displayName"] = "That display name is already used."
        if accepted_notice is not True:
            errors["acceptNotice"] = "Accept the conduct and privacy notice to create an account."  # OR-003
        if errors:
            return RegistrationResult(False, errors)

        if self.accounts.find_by_email(email) is not None:
            # FR-004: no second account; the caller shows one message that reveals nothing
            return RegistrationResult(True)
        account = self.accounts.add(Account(email, display_name, generate_password_hash(password, method=self.hash_method),
                                         notice_accepted_at=self.clock()))
        self._issue_token(account, is_resend=False)
        return RegistrationResult(True)

    def _issue_token(self, account: Account, is_resend: bool) -> None:
        now = self.clock()
        raw = secrets.token_urlsafe(32)
        life = self.settings.get(SettingName.VERIFICATION_LINK_LIFE)
        self.tokens.add(VerificationToken(account.id, hash_token(raw), expires_at=now + timedelta(hours=life),
                                          created_at=now, is_resend=is_resend))
        link = f"{self.base_url}/verify?token={raw}"
        self.gateway.send(EmailMessage(account.email, "Verify your StudBud account",
                                       f"Hi {account.display_name}, confirm your account: {link}"))

    # ---- verification (FR-005, FR-006) ----
    def verify(self, raw_token: str) -> Optional[Account]:
        now = self.clock()
        token = self.tokens.find_by_hash(hash_token(raw_token or ""))
        if token is None or not token.is_valid(now):
            return None
        account = self.accounts.get(token.account_id)
        if account is None or account.status != AccountStatus.UNVERIFIED:
            return None
        token.used_at = now
        self.tokens.save(token)
        account.status = AccountStatus.VERIFIED
        self.accounts.save(account)
        return account

    def resend_verification(self, email: str) -> ResendOutcome:
        """Always looks the same to the caller unless the hourly limit is hit for a real unverified account."""
        account = self.accounts.find_by_email(email or "")
        if account is None or account.status != AccountStatus.UNVERIFIED:
            return ResendOutcome.SENT
        now = self.clock()
        limit = self.settings.get(SettingName.RESEND_LIMIT)
        if self.tokens.count_resends_since(account.id, now - timedelta(hours=1)) >= limit:
            return ResendOutcome.LIMIT
        self.tokens.invalidate_all(account.id, now)  # earlier links stop working
        self._issue_token(account, is_resend=True)
        return ResendOutcome.SENT

    # ---- sign in (FR-007 to FR-009) ----
    def sign_in(self, email: str, password: str) -> SignInResult:
        now = self.clock()
        account = self.accounts.find_by_email(email or "")
        if account is None:
            generate_password_hash("x", method=self.hash_method)  # keep timing similar
            return SignInResult(SignInOutcome.INVALID)
        if account.is_locked(now):
            return SignInResult(SignInOutcome.LOCKED)
        if not check_password_hash(account.password_hash, password or ""):
            account.record_failed_sign_in(
                now, self.settings.get(SettingName.LOCKOUT_ATTEMPTS),
                self.settings.get(SettingName.LOCKOUT_WINDOW), self.settings.get(SettingName.LOCKOUT_PERIOD))
            self.accounts.save(account)
            return SignInResult(SignInOutcome.INVALID)
        if account.status == AccountStatus.UNVERIFIED:
            return SignInResult(SignInOutcome.UNVERIFIED)
        if account.status in (AccountStatus.SUSPENDED, AccountStatus.DELETED):
            return SignInResult(SignInOutcome.SUSPENDED)
        account.record_successful_sign_in(now)
        self.accounts.save(account)
        return SignInResult(SignInOutcome.OK, account)

    # ---- session (NFR-011, NFR-013) ----
    def start_session(self, session: dict, account: Account) -> None:
        session.clear()
        session["account_id"] = account.id
        session["last_seen"] = self.clock().timestamp()

    def current_account(self, session: dict) -> Optional[Account]:
        """None for a signed-out, idle or suspended session. Every protected call goes through here."""
        account_id, last_seen = session.get("account_id"), session.get("last_seen")
        if account_id is None or last_seen is None:
            return None
        now = self.clock()
        idle = timedelta(hours=self.settings.get(SettingName.SESSION_IDLE_TIME))
        if now - datetime.fromtimestamp(last_seen, tz=timezone.utc) > idle:
            session.clear()
            return None
        account = self.accounts.get(account_id)
        if account is None or account.status != AccountStatus.VERIFIED:
            session.clear()
            return None
        session["last_seen"] = now.timestamp()
        return account

    def sign_out(self, session: dict) -> None:
        session.clear()


@service("auth")
def build_auth_service(d):
    kwargs = {"clock": d.clock} if d.clock else {}
    return AuthService(d.accounts, d.tokens, d.settings, d.gateway, d.config["BASE_URL"],
                       hash_method=d.config["PASSWORD_HASH_METHOD"], **kwargs)
