"""Repositories for communities (D4) and posts and replies (D5)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from ..models.content import Community, Post, Reply

PAGE_SIZE = 20  # FR-034, FR-035


def _dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


def _s(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


class CommunityRepository(ABC):
    @abstractmethod
    def add(self, community): ...
    @abstractmethod
    def get(self, community_id: int): ...
    @abstractmethod
    def find_by_course(self, course_code: str): ...
    @abstractmethod
    def name_taken(self, name: str) -> bool: ...
    @abstractmethod
    def save(self, community): ...
    @abstractmethod
    def list_active(self, query: str = "") -> list: ...
    @abstractmethod
    def add_member(self, community_id: int, account_id: int) -> None: ...
    @abstractmethod
    def remove_member(self, community_id: int, account_id: int) -> None: ...
    @abstractmethod
    def is_member(self, community_id: int, account_id: int) -> bool: ...
    @abstractmethod
    def joined_ids(self, account_id: int) -> list: ...
    @abstractmethod
    def course_community_ids(self, account_id: int) -> list: ...


class PostRepository(ABC):
    @abstractmethod
    def add_post(self, post): ...
    @abstractmethod
    def get_post(self, post_id: int): ...
    @abstractmethod
    def save_post(self, post): ...
    @abstractmethod
    def add_reply(self, reply): ...
    @abstractmethod
    def get_reply(self, reply_id: int): ...
    @abstractmethod
    def save_reply(self, reply): ...
    @abstractmethod
    def replies_for(self, post_id: int) -> list: ...
    @abstractmethod
    def page(self, community_ids: list, kind: Optional[str], page: int, viewer_id: int, words: Optional[list] = None): ...


class SqliteCommunityRepository(CommunityRepository):
    def __init__(self, conn):
        self.conn = conn

    def _row(self, r):
        n = self.conn.execute("SELECT COUNT(*) c FROM community_members WHERE community_id=?", (r["id"],)).fetchone()["c"]
        return Community(name=r["name"], kind=r["kind"], course_code=r["course_code"], status=r["status"],
                         member_count=n, id=r["id"])

    def add(self, c):
        cur = self.conn.execute("INSERT INTO communities(name, kind, course_code, status) VALUES (?,?,?,?)",
                                (c.name, c.kind, c.course_code, c.status))
        self.conn.commit()
        c.id = cur.lastrowid
        return c

    def get(self, community_id):
        r = self.conn.execute("SELECT * FROM communities WHERE id=?", (community_id,)).fetchone()
        return self._row(r) if r else None

    def find_by_course(self, course_code):
        r = self.conn.execute("SELECT * FROM communities WHERE course_code=?", (course_code,)).fetchone()
        return self._row(r) if r else None

    def name_taken(self, name):
        return self.conn.execute("SELECT 1 FROM communities WHERE name=?", (name,)).fetchone() is not None

    def save(self, c):
        self.conn.execute("UPDATE communities SET name=?, status=? WHERE id=?", (c.name, c.status, c.id))
        self.conn.commit()

    def list_active(self, query=""):
        rows = self.conn.execute("SELECT * FROM communities WHERE status='active' AND name LIKE ? ORDER BY name",
                                 (f"%{query.strip()}%",)).fetchall()
        return [self._row(r) for r in rows]

    def add_member(self, community_id, account_id):
        self.conn.execute("INSERT OR IGNORE INTO community_members(community_id, account_id) VALUES (?,?)",
                          (community_id, account_id))
        self.conn.commit()

    def remove_member(self, community_id, account_id):
        self.conn.execute("DELETE FROM community_members WHERE community_id=? AND account_id=?", (community_id, account_id))
        self.conn.commit()

    def is_member(self, community_id, account_id):
        return self.conn.execute("SELECT 1 FROM community_members WHERE community_id=? AND account_id=?",
                                 (community_id, account_id)).fetchone() is not None

    def joined_ids(self, account_id):
        return [r["community_id"] for r in self.conn.execute(
            "SELECT community_id FROM community_members WHERE account_id=?", (account_id,))]

    def course_community_ids(self, account_id):
        return [r["community_id"] for r in self.conn.execute(
            "SELECT m.community_id FROM community_members m JOIN communities c ON c.id=m.community_id "
            "WHERE m.account_id=? AND c.kind='course'", (account_id,))]


class SqlitePostRepository(PostRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _post(r):
        return Post(community_id=r["community_id"], author_id=r["author_id"], kind=r["kind"], title=r["title"],
                    body=r["body"], created_at=_dt(r["created_at"]), status=r["status"],
                    edited_at=_dt(r["edited_at"]), id=r["id"])

    @staticmethod
    def _reply(r):
        return Reply(post_id=r["post_id"], author_id=r["author_id"], body=r["body"], created_at=_dt(r["created_at"]),
                     status=r["status"], edited_at=_dt(r["edited_at"]), id=r["id"])

    def add_post(self, p):
        cur = self.conn.execute(
            "INSERT INTO posts(community_id, author_id, kind, title, body, status, created_at) VALUES (?,?,?,?,?,?,?)",
            (p.community_id, p.author_id, p.kind, p.title, p.body, p.status, _s(p.created_at)))
        self.conn.commit()
        p.id = cur.lastrowid
        return p

    def get_post(self, post_id):
        r = self.conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        return self._post(r) if r else None

    def save_post(self, p):
        self.conn.execute("UPDATE posts SET title=?, body=?, status=?, edited_at=? WHERE id=?",
                          (p.title, p.body, p.status, _s(p.edited_at), p.id))
        self.conn.commit()

    def add_reply(self, rp):
        cur = self.conn.execute("INSERT INTO replies(post_id, author_id, body, status, created_at) VALUES (?,?,?,?,?)",
                                (rp.post_id, rp.author_id, rp.body, rp.status, _s(rp.created_at)))
        self.conn.commit()
        rp.id = cur.lastrowid
        return rp

    def get_reply(self, reply_id):
        r = self.conn.execute("SELECT * FROM replies WHERE id=?", (reply_id,)).fetchone()
        return self._reply(r) if r else None

    def save_reply(self, rp):
        self.conn.execute("UPDATE replies SET body=?, status=?, edited_at=? WHERE id=?",
                          (rp.body, rp.status, _s(rp.edited_at), rp.id))
        self.conn.commit()

    def replies_for(self, post_id):
        rows = self.conn.execute("SELECT * FROM replies WHERE post_id=? AND status != 'deleted' ORDER BY created_at, id",
                                 (post_id,)).fetchall()
        return [self._reply(r) for r in rows]

    def page(self, community_ids, kind, page, viewer_id, words=None):
        """Newest first, 20 per page. Hidden posts show only to their author; deleted posts never (FR-065, FR-033)."""
        if not community_ids:
            return [], False
        marks = ",".join("?" * len(community_ids))
        sql = (f"SELECT * FROM posts WHERE community_id IN ({marks}) AND status != 'deleted' "
               "AND (status = 'visible' OR author_id = ?)")
        args = [*community_ids, viewer_id]
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        for w in words or []:
            sql += " AND (title LIKE ? OR body LIKE ?)"
            args += [f"%{w}%", f"%{w}%"]
        sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        args += [PAGE_SIZE + 1, max(page - 1, 0) * PAGE_SIZE]
        rows = self.conn.execute(sql, args).fetchall()
        return [self._post(r) for r in rows[:PAGE_SIZE]], len(rows) > PAGE_SIZE
