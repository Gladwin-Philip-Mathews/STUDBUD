"""ModerationService (process 6.0, DFD-1): reports, queue, acknowledgement, decision, conduct action, case summary.

One public operation per child process: submit_report (6.1), open_queue (6.2), acknowledge (6.3), decide (6.4),
case_summary (6.6); apply_action implements 6.5. FR-053, FR-054, FR-060 to FR-070, BR-02, CON-005.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from ..container import service
from ..models import ConductAction, Decision, EventType, ItemRef, ReportReason, SafetyReport, ModerationOutcome
from ..models.enums import SettingName

MAX_TEXT = 500  # FR-060
MAX_NOTE = 1000
ITEM_TYPES = ("student", "post", "reply", "message")
RECENT_REPORT_DAYS = 30  # a closed report still protects its message for this long (OR-001)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ModResult:
    item: object = None
    errors: dict = field(default_factory=dict)
    not_found: bool = False
    case_summary: Optional[dict] = None  # DF-24, filled when a decision carried the escalation choice (DF-36)

    @property
    def ok(self) -> bool:
        return not self.errors and not self.not_found


@dataclass
class QueueItem:
    report: SafetyReport
    age_hours: float
    overdue: bool
    reporter_name: str
    reported_name: str
    item: Optional[dict]


class ModerationService:
    def __init__(self, accounts, reports, posts, messages, connections, communities, notifications, settings, audit,
                 clock: Callable[[], datetime] = utc_now):
        self.accounts, self.reports, self.posts, self.messages = accounts, reports, posts, messages
        self.connections, self.communities, self.notifications = connections, communities, notifications
        self.settings, self.audit, self.clock = settings, audit, clock

    # ---- 6.1 Validate and record report (FR-060, FR-061, FR-069) ----
    def _resolve(self, reporter_id: int, item_type: str, item_id):
        """Returns (reported_student_id, item_id) or None. The reporter must be able to see the item."""
        if item_type == "student":
            a = self.accounts.get(item_id) if isinstance(item_id, int) else None
            return (a.id, a.id) if a else None
        if item_type == "post":
            p = self.posts.get_post(item_id) if isinstance(item_id, int) else None
            if p and p.status == "visible" and self.communities.is_member(p.community_id, reporter_id):
                return p.author_id, p.id
        if item_type == "reply":
            r = self.posts.get_reply(item_id) if isinstance(item_id, int) else None
            p = self.posts.get_post(r.post_id) if r else None
            if r and r.status == "visible" and p and self.communities.is_member(p.community_id, reporter_id):
                return r.author_id, r.id
        if item_type == "message":
            m = self.messages.get(item_id) if isinstance(item_id, int) else None
            c = self.connections.get(m.connection_id) if m else None
            if m and m.status == "visible" and c and reporter_id in (c.requester_id, c.receiver_id):
                return m.sender_id, m.id
        return None

    def submit_report(self, reporter_id: int, item_type, item_id, reason, text="") -> ModResult:
        text = (text or "").strip()
        errors = {}
        if reason not in {r.value for r in ReportReason}:
            errors["reason"] = "Choose a reason."  # FR-069
        if len(text) > MAX_TEXT:
            errors["text"] = f"The text can be up to {MAX_TEXT} characters."  # AC-FR-060b
        if item_type not in ITEM_TYPES:
            return ModResult(not_found=True)
        found = self._resolve(reporter_id, item_type, item_id)
        if found is None:
            return ModResult(not_found=True)
        reported_id, resolved_item_id = found
        if reported_id == reporter_id:
            errors["item"] = "You cannot report yourself."  # FR-069
        if errors:
            return ModResult(errors=errors)
        # more than one report on the same item is accepted (FR-069)
        report = self.reports.save(SafetyReport(reporter_id, reported_id, item_type, resolved_item_id, reason, text,
                                                received_at=self.clock()))
        return ModResult(item=report)

    # ---- 6.2 Compile moderator queue (FR-054, FR-062) ----
    def _item_view(self, report: SafetyReport, moderator_id: int, audit: bool = True) -> Optional[dict]:
        """The reported item for a moderator. Message text is shown only for the message named in the report, and each
        access is recorded (FR-054). Hidden or deleted posts stay visible here (FR-033)."""
        t = report.item_type
        if t == "post":
            p = self.posts.get_post(report.item_id)
            return {"type": "post", "title": p.title, "text": p.body, "status": p.status} if p else None
        if t == "reply":
            r = self.posts.get_reply(report.item_id)
            return {"type": "reply", "text": r.body, "status": r.status} if r else None
        if t == "message":
            m = self.messages.get(report.item_id)
            if m is None:
                return None
            if audit:
                self.audit.record(moderator_id, "MESSAGE_ACCESS", f"report {report.id}", f"message {m.id}")
            return {"type": "message", "text": m.body, "status": m.status}
        return {"type": "student"}

    def open_queue(self, moderator_id: int) -> list:
        """Open reports oldest first with age, reason and reported item; overdue ones are flagged."""
        now = self.clock()
        limit = self.settings.duration(SettingName.OVERDUE_FLAG)
        result = []
        for r in self.reports.find_open():
            result.append(QueueItem(r, round((now - r.received_at).total_seconds() / 3600, 1), r.is_overdue(now, limit),
                                    self._name(r.reporter_id), self._name(r.reported_student_id),
                                    self._item_view(r, moderator_id)))
        return result

    def _name(self, account_id: int) -> str:
        a = self.accounts.get(account_id)
        return a.display_name if a else "deleted student"

    def report_context(self, moderator_id: int, report_id: int) -> ModResult:
        """What a moderator needs to investigate before acknowledging or deciding (FR-064): the reported post with its
        community, author and time, the whole thread when a post or reply is reported (hidden and deleted content stays
        visible to a moderator, FR-033), and the earlier reports about the same student with their outcomes. For a
        message only the reported message is shown, never the rest of the conversation (FR-054, AC-FR-070a)."""
        report = self.reports.get(report_id)
        if report is None:
            return ModResult(not_found=True)
        post = None
        reply_id = None
        if report.item_type == "post":
            post = self.posts.get_post(report.item_id)
        elif report.item_type == "reply":
            reply = self.posts.get_reply(report.item_id)
            post = self.posts.get_post(reply.post_id) if reply else None
            reply_id = reply.id if reply else None
        thread = None
        if post is not None:
            community = self.communities.get(post.community_id)
            thread = {
                "post": {"id": post.id, "community": community.name if community else "", "kind": post.kind,
                         "title": post.title, "text": post.body, "status": post.status,
                         "author": self._name(post.author_id), "createdAt": post.created_at,
                         "edited": post.edited_at is not None, "reported": report.item_type == "post"},
                "replies": [{"id": r.id, "author": self._name(r.author_id), "text": r.body, "status": r.status,
                             "createdAt": r.created_at, "edited": r.edited_at is not None, "reported": r.id == reply_id}
                            for r in self.posts.replies_for(post.id, include_deleted=True)],
            }
        history = []
        for other in self.reports.find_about_student(report.reported_student_id):
            if other.id == report.id:
                continue
            outcome = self.reports.get_outcome(other.id)
            history.append({"id": other.id, "reason": other.reason, "itemType": other.item_type,
                            "receivedAt": other.received_at, "status": other.status,
                            "decision": outcome.decision if outcome else None,
                            "action": outcome.action if outcome else None})
        return ModResult(item={"reportId": report.id, "reportedStudent": self._name(report.reported_student_id),
                               "thread": thread, "history": history})

    # ---- 6.3 Record acknowledgement (FR-063) ----
    def acknowledge(self, moderator_id: int, report_id: int) -> ModResult:
        report = self.reports.get(report_id)
        if report is None:
            return ModResult(not_found=True)
        if report.acknowledge(self.clock(), moderator_id):
            self.reports.save(report)
            self.notifications.notify(report.reporter_id, EventType.REPORT_ACKNOWLEDGED,
                                      "Your report was received and is being reviewed.", ItemRef("report", report.id))  # DF-26a
        return ModResult(item=report)

    # ---- 6.4 Record moderation decision (FR-064, FR-067, FR-068) ----
    def decide(self, moderator_id: int, report_id: int, decision, action, note, escalate: bool = False) -> ModResult:
        """DF-23 moderation decision: decision + action + note + (escalation choice, upheld only). On an upheld report
        with the escalation choice, 6.4 passes DF-36 to 6.6 and the case summary comes back with the outcome."""
        report = self.reports.get(report_id)
        if report is None:
            return ModResult(not_found=True)
        if report.status == "closed":
            return ModResult(errors={"decision": "This report is closed. Only a dated later note can be added."})  # FR-067
        note = (note or "").strip()
        errors = {}
        if decision not in {d.value for d in Decision}:
            errors["decision"] = "Choose upheld or dismissed."
        if action not in {a.value for a in ConductAction}:
            errors["action"] = "Choose an action."
        if not note or len(note) > MAX_NOTE:
            errors["note"] = "Write a note of up to 1000 characters."
        if not errors and decision == Decision.DISMISSED.value and action != ConductAction.NONE.value:
            errors["action"] = "A dismissed report has no action."
        if not errors and escalate and decision != Decision.UPHELD.value:
            errors["escalate"] = "Only an upheld report can be escalated to Student Affairs."
        if not errors and action == ConductAction.CONTENT_HIDDEN.value and report.item_type == "student":
            errors["action"] = "There is no content to hide on a student report."
        if not errors and report.acknowledged_at is None:
            errors["decision"] = "Acknowledge the report before deciding."
        if errors:
            return ModResult(errors=errors)
        outcome = ModerationOutcome(report_id, decision, action, note, self.clock(), moderator_id)
        self.reports.save_outcome(outcome)
        self.audit.record(moderator_id, "DECISION", f"report {report_id}", f"{decision}, {action}")  # NFR-015
        if action != ConductAction.NONE.value:
            self.apply_action(report, action)  # DF-35 to 6.5
        self.notifications.notify(report.reporter_id, EventType.REPORT_CLOSED,  # DF-26b; FR-068: no action, no name
                                  "Your report was reviewed and closed.", ItemRef("report", report_id))
        summary = None
        if escalate:  # DF-36 escalation request to 6.6
            summary = self.case_summary(moderator_id, report_id).item
            self.audit.record(moderator_id, "ESCALATION", f"report {report_id}", "case summary prepared for Student Affairs")
        return ModResult(item=outcome, case_summary=summary)

    # ---- 6.5 Apply conduct action (FR-065, FR-066) ----
    def apply_action(self, report: SafetyReport, action: str) -> None:
        if action == ConductAction.CONTENT_HIDDEN.value:
            if report.item_type == "post":
                item = self.posts.get_post(report.item_id)
                save = self.posts.save_post
            elif report.item_type == "reply":
                item = self.posts.get_reply(report.item_id)
                save = self.posts.save_reply
            else:
                item = self.messages.get(report.item_id)
                save = self.messages.save
            if item is not None:
                item.hide()  # Reportable.hide()
                save(item)
        elif action == ConductAction.ACCOUNT_SUSPENDED.value:
            account = self.accounts.get(report.reported_student_id)
            if account is not None:
                account.suspend()  # ends every session at the next request (FR-066)
                self.accounts.save(account)

    def add_later_note(self, moderator_id: int, report_id: int, note) -> ModResult:
        report = self.reports.get(report_id)
        note = (note or "").strip()
        if report is None:
            return ModResult(not_found=True)
        if report.status != "closed":
            return ModResult(errors={"note": "Record the decision first."})
        if not note or len(note) > MAX_NOTE:
            return ModResult(errors={"note": "Write a note of up to 1000 characters."})
        self.reports.add_note(report_id, note, self.clock(), moderator_id)  # the only permitted change (FR-067)
        return ModResult(item=self.reports.get_outcome(report_id))

    # ---- 6.6 Produce case summary (FR-070) ----
    def case_summary(self, moderator_id: int, report_id: int) -> ModResult:
        report = self.reports.get(report_id)
        outcome = self.reports.get_outcome(report_id) if report else None
        if report is None:
            return ModResult(not_found=True)
        if outcome is None or outcome.decision != Decision.UPHELD.value:
            return ModResult(errors={"summary": "A case summary is available only for an upheld report."})
        item = self._item_view(report, moderator_id)  # only the reported item, never other messages (AC-FR-070a)
        return ModResult(item={
            "reportId": report.id, "reason": report.reason, "reportedStudent": self._name(report.reported_student_id),
            "receivedAt": report.received_at, "acknowledgedAt": report.acknowledged_at,
            "decision": outcome.decision, "action": outcome.action, "decidedAt": outcome.decided_at, "note": outcome.note,
            "reportedItem": item})

    def get_outcome(self, report_id: int):
        return self.reports.get_outcome(report_id)

    def retention_keep_ids(self) -> set:
        """Messages that retention must not delete (OR-001)."""
        return self.reports.protected_message_ids(self.clock() - timedelta(days=RECENT_REPORT_DAYS))


@service("moderation")
def build_moderation_service(d):
    from ..container import get_service
    kwargs = {"clock": d.clock} if d.clock else {}
    return ModerationService(d.accounts, d.reports, d.posts, d.messages, d.connections, d.communities,
                             get_service("notifications"), d.settings, get_service("audit"), **kwargs)
