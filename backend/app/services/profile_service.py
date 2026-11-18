"""ProfileService (process 2.0): profile rules, what others may see, and account deletion.

FR-010 to FR-015, DR-002, DR-003. Interests, courses and year are optional; intent and cohort are required.
"""
from dataclasses import dataclass, field
from typing import Optional

from werkzeug.security import check_password_hash

from ..container import service
from ..models import Profile
from ..models.enums import AccountStatus, Cohort, ConnectionIntent

MAX_INTERESTS, MAX_INTEREST_LENGTH = 20, 30  # FR-012, DR-002


@dataclass
class ProfileResult:
    profile: Optional[Profile] = None
    errors: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


class ProfileService:
    def __init__(self, accounts, profiles, courses, connections, notifications, tokens):
        self.accounts, self.profiles, self.courses = accounts, profiles, courses
        self.connections, self.notifications, self.tokens = connections, notifications, tokens

    def get(self, account_id: int) -> Optional[Profile]:
        return self.profiles.get(account_id)

    def is_complete(self, account_id: int) -> bool:
        """FR-010: other features open only once the profile has an intent and a cohort."""
        return self.profiles.get(account_id) is not None

    def save(self, account_id: int, intent, cohort, year_of_study=None, interests=None, course_codes=None) -> ProfileResult:
        errors = {}
        if intent not in {i.value for i in ConnectionIntent}:
            errors["intent"] = "Choose friendship, study partner or both."  # AC-FR-010a names the missing item
        if cohort not in {c.value for c in Cohort}:
            errors["cohort"] = "Choose a cohort answer."
        if year_of_study in ("", None):
            year_of_study = None
        elif not isinstance(year_of_study, int) or isinstance(year_of_study, bool) or not 1 <= year_of_study <= 8:
            errors["yearOfStudy"] = "Year of study is a number from 1 to 8."

        clean_interests = []
        for item in interests or []:
            text = (item or "").strip() if isinstance(item, str) else ""
            if not 1 <= len(text) <= MAX_INTEREST_LENGTH:
                errors["interests"] = f"Each interest is 1 to {MAX_INTEREST_LENGTH} characters."  # AC-FR-012a
                break
            if text.lower() not in {i.lower() for i in clean_interests}:
                clean_interests.append(text)
        if len(clean_interests) > MAX_INTERESTS:
            errors["interests"] = f"You can add up to {MAX_INTERESTS} interests."

        clean_courses = []
        for code in course_codes or []:
            course = self.courses.find_by_code(code) if isinstance(code, str) else None
            if course is None or course.status != "active":
                errors["courses"] = "Only courses from the course list can be added."  # AC-FR-011a
                break
            if course.code not in clean_courses:
                clean_courses.append(course.code)
        if errors:
            return ProfileResult(errors=errors)

        profile = Profile(account_id=account_id, intent=intent, cohort=cohort, year_of_study=year_of_study,
                          interests=clean_interests, course_codes=clean_courses)
        self.profiles.save(profile)
        return ProfileResult(profile=profile)

    def search_courses(self, query: str) -> list:
        return self.courses.active_matching(query)

    def public_view(self, target_id: int) -> Optional[dict]:
        """FR-014: only display name, interests, courses and intent. Never email, year of study or cohort."""
        account = self.accounts.get(target_id)
        profile = self.profiles.get(target_id)
        if account is None or profile is None or account.status != AccountStatus.VERIFIED:
            return None
        return {"id": account.id, "displayName": account.display_name, "interests": profile.interests,
                "courses": profile.course_codes, "intent": profile.intent}

    def delete_account(self, account_id: int, password: str) -> bool:
        """FR-015: after the password is entered again, remove profile, connections, notifications and credentials.
        Posts and replies stay and show the author as "deleted student" (the account row is kept, erased)."""
        account = self.accounts.get(account_id)
        if account is None or not check_password_hash(account.password_hash, password or ""):
            return False
        self.connections.delete_for_account(account_id)  # messages go with their connection (DR-008)
        self.notifications.delete_for_recipient(account_id)
        self.profiles.delete(account_id)
        self.accounts.erase(account_id)
        return True


@service("profiles")
def build_profile_service(d):
    return ProfileService(d.accounts, d.profiles, d.courses, d.connections, d.notifications, d.tokens)
