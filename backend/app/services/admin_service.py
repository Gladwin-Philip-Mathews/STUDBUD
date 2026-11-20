"""AdminService (process 9.0): courses, accepted domains, communities, roles, settings and system status.

FR-100 to FR-104, DR-013, DR-014, NFR-012. Role, community and setting changes are written to the audit record
(FR-102, NFR-015).
"""
import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from ..container import service
from ..models import AcceptedDomain, AccountStatus, Course, Role
from ..models.enums import SettingName

DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
CODE = re.compile(r"^[A-Z0-9][A-Z0-9 -]{1,19}$")
SETTING_RANGE = (1, 10000)
ACTIVE_DAYS = 7  # FR-103


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AdminResult:
    item: object = None
    errors: dict = field(default_factory=dict)
    not_found: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors and not self.not_found


@dataclass
class ImportResult:
    added: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    invalid: list = field(default_factory=list)


class AdminService:
    def __init__(self, accounts, courses, domains, stats, settings, audit, communities,
                 clock: Callable[[], datetime] = utc_now):
        self.accounts, self.courses, self.domains, self.stats = accounts, courses, domains, stats
        self.settings, self.audit, self.communities, self.clock = settings, audit, communities, clock

    # ---- courses (FR-100, FR-020) ----
    def list_courses(self) -> list:
        return self.courses.all()

    def add_course(self, admin_id: int, code, title) -> AdminResult:
        code, title = (code or "").strip().upper(), (title or "").strip()
        errors = {}
        if not CODE.match(code):
            errors["code"] = "Enter a course code such as SWEN-261."
        if not 1 <= len(title) <= 100:
            errors["title"] = "The title is 1 to 100 characters."
        if not errors and self.courses.find_by_code(code):
            errors["code"] = "This course code is already on the list."
        if errors:
            return AdminResult(errors=errors)
        course = self.courses.add(Course(code, title))
        self.communities.ensure_course_community(course)  # FR-020: one community per course
        self.audit.record(admin_id, "COURSE_ADDED", code)
        return AdminResult(item=course)

    def rename_course(self, admin_id: int, code, title) -> AdminResult:
        course = self.courses.find_by_code(code)
        title = (title or "").strip()
        if course is None:
            return AdminResult(not_found=True)
        if not 1 <= len(title) <= 100:
            return AdminResult(errors={"title": "The title is 1 to 100 characters."})
        course.name = title
        self.courses.save(course)
        self.audit.record(admin_id, "COURSE_RENAMED", course.code)
        return AdminResult(item=course)

    def archive_course(self, admin_id: int, code) -> AdminResult:
        """FR-100b, FR-025: students can no longer add it, members keep it, posts stay readable."""
        course = self.courses.find_by_code(code)
        if course is None:
            return AdminResult(not_found=True)
        course.status = "archived"
        self.courses.save(course)
        community = self.communities.communities.find_by_course(course.code)
        if community is not None:
            self.communities.archive(community.id)
        self.audit.record(admin_id, "COURSE_ARCHIVED", course.code)
        return AdminResult(item=course)

    def import_courses(self, admin_id: int, text: str) -> ImportResult:
        """AC-FR-100a: valid rows are added, duplicates and invalid rows are listed."""
        result = ImportResult()
        for number, row in enumerate(csv.reader(io.StringIO(text or "")), start=1):
            if not row or not "".join(row).strip():
                continue
            code = (row[0] if row else "").strip().upper()
            title = (row[1] if len(row) > 1 else "").strip()
            if number == 1 and code.lower() == "code":
                continue  # header row
            if self.courses.find_by_code(code) or code in result.added:
                result.duplicates.append(code)
                continue
            added = self.add_course(admin_id, code, title)
            if added.ok:
                result.added.append(code)
            else:
                result.invalid.append(f"row {number}")
        return result

    # ---- accepted domains (FR-101, DR-013) ----
    def list_domains(self) -> list:
        return self.domains.list()

    def add_domain(self, admin_id: int, domain) -> AdminResult:
        domain = (domain or "").strip().lower().lstrip("@")
        if not DOMAIN.match(domain):
            return AdminResult(errors={"domain": "Enter a domain such as g.rit.edu."})
        if self.domains.exists(domain):
            return AdminResult(errors={"domain": "This domain is already accepted."})
        added = self.domains.add(AcceptedDomain(domain, self.clock(), admin_id))
        self.audit.record(admin_id, "DOMAIN_ADDED", domain)
        return AdminResult(item=added)

    def remove_domain(self, admin_id: int, domain) -> AdminResult:
        domain = (domain or "").strip().lower()
        if not self.domains.remove(domain):
            return AdminResult(not_found=True)
        self.audit.record(admin_id, "DOMAIN_REMOVED", domain)  # takes effect at once for new registrations
        return AdminResult()

    # ---- interest communities (FR-102) ----
    def create_interest_community(self, admin_id: int, name) -> AdminResult:
        made = self.communities.create_interest_community(name)
        if made.ok:
            self.audit.record(admin_id, "COMMUNITY_CREATED", made.item.name)
        return AdminResult(item=made.item, errors=made.errors)

    def rename_community(self, admin_id: int, community_id: int, name) -> AdminResult:
        repo = self.communities.communities
        community = repo.get(community_id)
        name = (name or "").strip()
        if community is None or community.kind != "interest":
            return AdminResult(not_found=True)
        if not 3 <= len(name) <= 50:
            return AdminResult(errors={"name": "The name is 3 to 50 characters."})
        if name.lower() != community.name.lower() and repo.name_taken(name):
            return AdminResult(errors={"name": "Another community already uses this name."})
        community.name = name
        repo.save(community)
        self.audit.record(admin_id, "COMMUNITY_RENAMED", name)
        return AdminResult(item=community)

    def archive_community(self, admin_id: int, community_id: int) -> AdminResult:
        community = self.communities.communities.get(community_id)
        if community is None or community.kind != "interest":
            return AdminResult(not_found=True)
        self.communities.archive(community_id)
        self.audit.record(admin_id, "COMMUNITY_ARCHIVED", community.name)
        return AdminResult(item=community)

    # ---- roles (FR-102) ----
    def set_moderator(self, admin_id: int, email, enable: bool) -> AdminResult:
        account = self.accounts.find_by_email((email or "").strip())
        if account is None or account.status != AccountStatus.VERIFIED or account.role == Role.ADMINISTRATOR:
            return AdminResult(errors={"email": "Choose a verified student."})
        account.role = Role.MODERATOR if enable else Role.STUDENT
        self.accounts.save(account)
        self.audit.record(admin_id, "ROLE_ASSIGNED" if enable else "ROLE_REMOVED", f"account {account.id}",
                          account.role.value)
        return AdminResult(item=account)

    def moderators(self) -> list:
        return self.accounts.with_role(Role.MODERATOR)

    # ---- settings (FR-104, DR-014) ----
    def list_settings(self) -> list:
        return [x.as_dict() for x in self.settings.all()]

    def update_setting(self, admin_id: int, name, value) -> AdminResult:
        if name not in {n.value for n in SettingName}:
            return AdminResult(errors={"name": "This is not a setting."})  # DR-014
        if not isinstance(value, int) or isinstance(value, bool) or not SETTING_RANGE[0] <= value <= SETTING_RANGE[1]:
            return AdminResult(errors={"value": "Enter a whole number from 1 to 10000."})
        self.settings.set(name, value, changed_by=admin_id)  # applies to new events at once
        self.audit.record(admin_id, "SETTING_CHANGED", name, str(value))
        return AdminResult(item=self.list_settings())

    # ---- system status (FR-103) ----
    def status(self) -> dict:
        return self.stats.status_counts(self.clock() - timedelta(days=ACTIVE_DAYS))


@service("admin")
def build_admin_service(d):
    from ..container import get_service
    kwargs = {"clock": d.clock} if d.clock else {}
    return AdminService(d.accounts, d.courses, d.domains, d.stats, d.settings, get_service("audit"),
                        get_service("communities"), **kwargs)
