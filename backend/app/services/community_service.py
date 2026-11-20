"""CommunityService (process 3.0): communities, posts, replies, feed and search.

FR-020 to FR-025, FR-030 to FR-037. A reply raises REPLY_ADDED through NotificationService (DF-11).
Hidden content shows only to its author (FR-065); deleted content is soft-deleted so a moderator can still
see what an open report names (FR-033).
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from ..container import service
from ..models import AccountStatus, Community, EventType, ItemRef, Post, PostKind, Reply

POST_KINDS = tuple(k.value for k in PostKind)  # DR-005
TITLE = (5, 120)
TEXT = (1, 2000)
REPLY = (1, 1000)
COMMUNITY_NAME = (3, 50)
MIN_SEARCH = 2  # FR-036
REPEAT_WINDOW = timedelta(minutes=5)  # NFR-008: the same post submitted again inside this window is not duplicated


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ContentResult:
    item: object = None
    errors: dict = field(default_factory=dict)
    not_found: bool = False
    repeated: bool = False  # NFR-008: the action was a repeat of one already stored; nothing new was created

    @property
    def ok(self) -> bool:
        return not self.errors and not self.not_found


class CommunityService:
    def __init__(self, accounts, profiles, communities, posts, notifications, clock: Callable[[], datetime] = utc_now):
        self.accounts, self.profiles, self.communities = accounts, profiles, communities
        self.posts, self.notifications, self.clock = posts, notifications, clock

    # ---- communities (FR-020 to FR-025) ----
    def ensure_course_community(self, course) -> Community:
        """FR-020: one community per course."""
        existing = self.communities.find_by_course(course.code)
        if existing:
            return existing
        return self.communities.add(Community(name=f"{course.code} {course.name}", kind="course", course_code=course.code))

    def create_interest_community(self, name: str) -> ContentResult:
        name = (name or "").strip()
        if not COMMUNITY_NAME[0] <= len(name) <= COMMUNITY_NAME[1]:
            return ContentResult(errors={"name": "The name is 3 to 50 characters."})  # FR-021
        if self.communities.name_taken(name):
            return ContentResult(errors={"name": "Another community already uses this name."})
        return ContentResult(item=self.communities.add(Community(name=name, kind="interest")))

    def archive(self, community_id: int) -> bool:
        """FR-025: posts stay readable to members; new posts and replies are refused."""
        c = self.communities.get(community_id)
        if c is None:
            return False
        c.status = "archived"
        self.communities.save(c)
        return True

    def list_for(self, account_id: int, query: str = "") -> list:
        """FR-024: active communities with name, kind, member count and whether the student has joined."""
        joined = set(self.communities.joined_ids(account_id))
        return [(c, c.id in joined) for c in self.communities.list_active(query)]

    def join(self, account_id: int, community_id: int) -> bool:
        c = self.communities.get(community_id)
        if c is None or not c.is_active():
            return False
        if c.kind == "course":  # FR-023: only for a course on the student's profile
            profile = self.profiles.get(account_id)
            if profile is None or c.course_code not in profile.course_codes:
                return False
        self.communities.add_member(community_id, account_id)
        return True

    def leave(self, account_id: int, community_id: int) -> None:
        self.communities.remove_member(community_id, account_id)

    # ---- posts (FR-030 to FR-033) ----
    def create_post(self, author_id: int, community_id: int, kind, title, text) -> ContentResult:
        c = self.communities.get(community_id)
        if c is None or not self.communities.is_member(community_id, author_id):
            return ContentResult(not_found=True)
        title, text = (title or "").strip(), (text or "").strip()
        errors = {}
        if kind not in POST_KINDS:
            errors["kind"] = "Choose question, share or study partner request."
        if not TITLE[0] <= len(title) <= TITLE[1]:
            errors["title"] = "The title is 5 to 120 characters."
        if not TEXT[0] <= len(text) <= TEXT[1]:
            errors["text"] = "The text is 1 to 2000 characters."
        if not c.is_active():
            errors["community"] = "This community is archived, so new posts are not accepted."
        if errors:
            return ContentResult(errors=errors)
        now = self.clock()
        # NFR-008: when a student repeats the submission after a failure or a double click, one post exists.
        same = self.posts.find_same_post_since(author_id, community_id, kind, title, text, now - REPEAT_WINDOW)
        if same is not None:
            return ContentResult(item=same, repeated=True)
        post = self.posts.add_post(Post(community_id, author_id, kind, title, text, created_at=now))
        return ContentResult(item=post)

    def reply(self, author_id: int, post_id: int, text) -> ContentResult:
        post = self.posts.get_post(post_id)
        if post is None or post.status == "deleted" or not self.communities.is_member(post.community_id, author_id):
            return ContentResult(not_found=True)
        text = (text or "").strip()
        if not REPLY[0] <= len(text) <= REPLY[1]:
            return ContentResult(errors={"text": "The reply is 1 to 1000 characters."})
        if not self.communities.get(post.community_id).is_active():
            return ContentResult(errors={"community": "This community is archived, so new replies are not accepted."})
        reply = self.posts.add_reply(Reply(post_id, author_id, text, created_at=self.clock()))
        if post.author_id != author_id:  # FR-032, FR-080
            me = self.accounts.get(author_id)
            self.notifications.notify(post.author_id, EventType.REPLY_ADDED, f"{me.display_name} replied to your post.",
                                      ItemRef("post", post.id))  # DF-11
        return ContentResult(item=reply)

    def _own(self, item, account_id):
        return item is not None and item.author_id == account_id and item.status != "deleted"

    def edit_post(self, account_id: int, post_id: int, title, text) -> ContentResult:
        post = self.posts.get_post(post_id)
        if not self._own(post, account_id):
            return ContentResult(not_found=True)
        if not post.can_edit(self.clock()):
            return ContentResult(errors={"edit": "A post can be edited for 15 minutes after it is posted."})
        title, text = (title or "").strip(), (text or "").strip()
        errors = {}
        if not TITLE[0] <= len(title) <= TITLE[1]:
            errors["title"] = "The title is 5 to 120 characters."
        if not TEXT[0] <= len(text) <= TEXT[1]:
            errors["text"] = "The text is 1 to 2000 characters."
        if errors:
            return ContentResult(errors=errors)
        post.title, post.body, post.edited_at = title, text, self.clock()
        self.posts.save_post(post)
        return ContentResult(item=post)

    def edit_reply(self, account_id: int, reply_id: int, text) -> ContentResult:
        reply = self.posts.get_reply(reply_id)
        if not self._own(reply, account_id):
            return ContentResult(not_found=True)
        if not reply.can_edit(self.clock()):
            return ContentResult(errors={"edit": "A reply can be edited for 15 minutes after it is posted."})
        text = (text or "").strip()
        if not REPLY[0] <= len(text) <= REPLY[1]:
            return ContentResult(errors={"text": "The reply is 1 to 1000 characters."})
        reply.body, reply.edited_at = text, self.clock()
        self.posts.save_reply(reply)
        return ContentResult(item=reply)

    def delete_post(self, account_id: int, post_id: int) -> bool:
        post = self.posts.get_post(post_id)
        if not self._own(post, account_id):
            return False
        post.status = "deleted"  # soft delete: an open safety report can still show it to a moderator (FR-033)
        self.posts.save_post(post)
        return True

    def delete_reply(self, account_id: int, reply_id: int) -> bool:
        reply = self.posts.get_reply(reply_id)
        if not self._own(reply, account_id):
            return False
        reply.status = "deleted"
        self.posts.save_reply(reply)
        return True

    # ---- reading (FR-034 to FR-037) ----
    def feed(self, viewer_id: int, kind: Optional[str] = None, page: int = 1):
        return self.posts.page(self.communities.joined_ids(viewer_id), kind, page, viewer_id)

    def community_posts(self, viewer_id: int, community_id: int, kind: Optional[str] = None, page: int = 1):
        if self.communities.get(community_id) is None or not self.communities.is_member(community_id, viewer_id):
            return None
        return self.posts.page([community_id], kind, page, viewer_id)

    def search(self, viewer_id: int, query: str, kind: Optional[str] = None, page: int = 1):
        """FR-036: at least 2 characters, words must all appear in the title or text, joined communities only."""
        words = (query or "").split()
        if len((query or "").strip()) < MIN_SEARCH:
            return None
        return self.posts.page(self.communities.joined_ids(viewer_id), kind, page, viewer_id, words)

    def get_post(self, viewer_id: int, post_id: int):
        """FR-035: the post with its replies in time order, for members only. Hidden content shows only to its author."""
        post = self.posts.get_post(post_id)
        if post is None or post.status == "deleted" or not self.communities.is_member(post.community_id, viewer_id):
            return None
        if post.status == "hidden" and post.author_id != viewer_id:
            return None
        replies = [r for r in self.posts.replies_for(post_id) if r.status == "visible" or r.author_id == viewer_id]
        return post, replies

    # ---- shared helpers for controllers ----
    def author_name(self, account_id: int) -> str:
        a = self.accounts.get(account_id)
        if a is None or a.status == AccountStatus.DELETED:
            return "deleted student"  # FR-015
        return a.display_name


@service("communities")
def build_community_service(d):
    from ..container import get_service
    kwargs = {"clock": d.clock} if d.clock else {}
    return CommunityService(d.accounts, d.profiles, d.communities, d.posts, get_service("notifications"), **kwargs)
