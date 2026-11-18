"""PilotMeasuresService (process 8.0): the onboarding question and the pilot measures report.

FR-090 to FR-094, G-01 to G-03, DR-012, NFR-024. The report contains numbers only and never a name or an email
address (FR-094). A cohort group of fewer than 5 students is combined with another group (FR-093).

Assumption (documented in the test report): pilot week 1 starts when the first account was created, so week 12 starts
77 days later. Active users are verified students who signed in during the 7 days before the report.
"""
import csv
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from ..container import service
from ..models.pilot import ANSWERS, CohortRow, OnboardingAnswer

MIN_GROUP = 5  # FR-093
ACCEPT_WINDOW = timedelta(days=7)  # G-01
ACK_WINDOW = timedelta(hours=48)  # G-03
ACTIVE_WINDOW = timedelta(days=7)
STUDY_INTENTS = ("study partner", "both")
SCALE = {"0": 0, "1 to 2": 1, "3 to 5": 2, "more than 5": 3}  # skipped is left out of the change measure


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def pct(part: int, whole: int) -> Optional[float]:
    return round(100 * part / whole, 1) if whole else None


def merge_small_groups(sizes: dict) -> dict:
    """Maps each cohort to the label it is reported under. Groups under 5 students are combined into "other", and if
    "other" is still under 5 it is combined with the smallest remaining group, never shown on its own (AC-FR-093a)."""
    big = {c: n for c, n in sizes.items() if n >= MIN_GROUP}
    small = {c: n for c, n in sizes.items() if n < MIN_GROUP}
    mapping = {c: c for c in big}
    if not small:
        return mapping
    if sum(small.values()) < MIN_GROUP and big:
        target = min(big, key=lambda c: (big[c], c))
        label = f"other + {target}"
        mapping[target] = label
    else:
        label = "other"
    mapping.update({c: label for c in small})
    return mapping


class PilotMeasuresService:
    def __init__(self, accounts, profiles, onboarding, data, clock: Callable[[], datetime] = utc_now):
        self.accounts, self.profiles, self.onboarding, self.data, self.clock = accounts, profiles, onboarding, data, clock

    # ---- onboarding question (FR-090) ----
    def pilot_week(self, now: datetime) -> int:
        start = self.data.first_registration() or now
        return (now - start).days // 7 + 1

    def pending_question(self, account_id: int) -> Optional[int]:
        """The week (1 or 12) of the question the student should see now, or None."""
        account, profile = self.accounts.get(account_id), self.profiles.get(account_id)
        if account is None or profile is None or account.status.value != "verified":
            return None
        now = self.clock()
        if now - account.created_at <= timedelta(days=7) and not self.onboarding.find(account_id, 1):
            return 1
        if self.pilot_week(now) >= 12 and account.created_at < now and not self.onboarding.find(account_id, 12):
            return 12
        return None

    def answer(self, account_id: int, answer) -> Optional[OnboardingAnswer]:
        """Stores the answer (or "skipped") with the cohort and the week. Returns None when no question is due."""
        week = self.pending_question(account_id)
        if week is None or answer not in ANSWERS:
            return None
        cohort = self.profiles.get(account_id).cohort
        return self.onboarding.add(OnboardingAnswer(account_id, week, answer, cohort, self.clock()))

    # ---- pilot report (FR-092, FR-093) ----
    def report(self) -> dict:
        now = self.clock()
        students = self.data.students()
        sizes = Counter(cohort for _, cohort in students)
        label = merge_small_groups(dict(sizes))
        rows: dict = {}

        def row(cohort) -> CohortRow:
            name = label.get(cohort or "unknown", cohort or "unknown")
            if name not in rows:
                rows[name] = CohortRow(cohort=name, students=0)
            return rows[name]

        for name in set(label.values()):
            rows[name] = CohortRow(cohort=name, students=0)
        for _, cohort in students:
            row(cohort).students += 1

        # G-01: study partner requests and the share accepted within 7 days
        sent, accepted = Counter(), Counter()
        for r in self.data.request_rows():
            if r["intent"] not in STUDY_INTENTS:
                continue
            name = row(r["cohort"]).cohort
            sent[name] += 1
            if r["outcome"] == "accepted" and r["outcome_at"] - r["sent_at"] <= ACCEPT_WINDOW:
                accepted[name] += 1
        # G-02: answers in week 1 and week 12, and the change for students who answered both
        by_student = defaultdict(dict)
        for a in self.onboarding.all():
            target = row(a.cohort)
            (target.week1_answers if a.week == 1 else target.week12_answers)[a.answer] = (
                (target.week1_answers if a.week == 1 else target.week12_answers).get(a.answer, 0) + 1)
            if a.account_id is not None:
                by_student[a.account_id][a.week] = a
        for weeks in by_student.values():
            if 1 in weeks and 12 in weeks:
                target = row(weeks[12].cohort)
                target.answered_both += 1
                if weeks[1].answer in SCALE and weeks[12].answer in SCALE and SCALE[weeks[12].answer] > SCALE[weeks[1].answer]:
                    target.contact_increased += 1
        # G-03: safety reports, share acknowledged within 48 hours, upheld per 100 active users
        reports, acked, upheld = Counter(), Counter(), Counter()
        for r in self.data.report_rows():
            name = row(r["cohort"]).cohort
            reports[name] += 1
            if r["acknowledged_at"] is not None and r["acknowledged_at"] - r["received_at"] <= ACK_WINDOW:
                acked[name] += 1
            if r["decision"] == "upheld":
                upheld[name] += 1
        active = Counter(row(c).cohort for c in self.data.active_cohorts(now - ACTIVE_WINDOW))

        for name, out in rows.items():
            out.requests_sent = sent[name]
            out.accepted_within_7_days_pct = pct(accepted[name], sent[name])
            out.safety_reports = reports[name]
            out.acknowledged_within_48h_pct = pct(acked[name], reports[name])
            out.upheld_reports = upheld[name]
            out.active_users = active[name]
            out.upheld_per_100_active = round(100 * upheld[name] / active[name], 1) if active[name] else None
        return {"groups": sorted(rows.values(), key=lambda r: r.cohort), "weekly": self._weekly(), "pilotWeek": self.pilot_week(now)}

    def _weekly(self) -> list:
        start = self.data.first_registration()
        if start is None:
            return []
        sent, accepted, reports = Counter(), Counter(), Counter()
        for r in self.data.request_rows():
            if r["intent"] not in STUDY_INTENTS:
                continue
            week = (r["sent_at"] - start).days // 7 + 1
            sent[week] += 1
            if r["outcome"] == "accepted" and r["outcome_at"] - r["sent_at"] <= ACCEPT_WINDOW:
                accepted[week] += 1
        for r in self.data.report_rows():
            reports[(r["received_at"] - start).days // 7 + 1] += 1
        weeks = sorted(set(sent) | set(reports))
        return [{"week": w, "requestsSent": sent[w], "acceptedWithin7DaysPct": pct(accepted[w], sent[w]),
                 "safetyReports": reports[w]} for w in weeks]

    def report_csv(self) -> str:
        """FR-094: for the Office of Student Affairs. Numbers only: no display name and no email address."""
        data = self.report()
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["cohort", "students", "study_partner_requests", "accepted_within_7_days_pct", "week1_answers",
                    "week12_answers", "answered_both", "contact_increased", "safety_reports",
                    "acknowledged_within_48h_pct", "upheld_reports", "active_users", "upheld_per_100_active"])
        for g in data["groups"]:
            w.writerow([g.cohort, g.students, g.requests_sent, g.accepted_within_7_days_pct,
                        ";".join(f"{k}={v}" for k, v in sorted(g.week1_answers.items())),
                        ";".join(f"{k}={v}" for k, v in sorted(g.week12_answers.items())),
                        g.answered_both, g.contact_increased, g.safety_reports, g.acknowledged_within_48h_pct,
                        g.upheld_reports, g.active_users, g.upheld_per_100_active])
        w.writerow([])
        w.writerow(["pilot_week", "study_partner_requests", "accepted_within_7_days_pct", "safety_reports"])
        for x in data["weekly"]:
            w.writerow([x["week"], x["requestsSent"], x["acceptedWithin7DaysPct"], x["safetyReports"]])
        return out.getvalue()


@service("pilot")
def build_pilot_service(d):
    kwargs = {"clock": d.clock} if d.clock else {}
    return PilotMeasuresService(d.accounts, d.profiles, d.onboarding, d.pilot_data, **kwargs)
