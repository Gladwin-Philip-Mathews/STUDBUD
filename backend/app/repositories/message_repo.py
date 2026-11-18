"""Repository for messages (D7)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from ..models.content import Message


def _dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


def _s(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


class MessageRepository(ABC):
    @abstractmethod
    def add(self, message): ...
    @abstractmethod
    def get(self, message_id: int): ...
    @abstractmethod
    def save(self, message): ...
    @abstractmethod
    def for_connection(self, connection_id: int) -> list:
        """All messages of a connection in time order."""
    @abstractmethod
    def unread_count(self, connection_id: int, reader_id: int) -> int: ...
    @abstractmethod
    def mark_read(self, connection_id: int, reader_id: int, now) -> None: ...
    @abstractmethod
    def last_sent_at(self, connection_id: int): ...
    @abstractmethod
    def purge_before(self, cutoff, keep_ids: set) -> int:
        """Delete messages sent before the cutoff except the ones in keep_ids (OR-001). Returns how many."""


class SqliteMessageRepository(MessageRepository):
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _row(r):
        return Message(connection_id=r["connection_id"], sender_id=r["sender_id"], body=r["body"],
                       sent_at=_dt(r["sent_at"]), status=r["status"], read_at=_dt(r["read_at"]), id=r["id"])

    def add(self, m):
        cur = self.conn.execute(
            "INSERT INTO messages(connection_id, sender_id, body, status, sent_at) VALUES (?,?,?,?,?)",
            (m.connection_id, m.sender_id, m.body, m.status, _s(m.sent_at)))
        self.conn.commit()
        m.id = cur.lastrowid
        return m

    def get(self, message_id):
        r = self.conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        return self._row(r) if r else None

    def save(self, m):
        self.conn.execute("UPDATE messages SET status=?, read_at=? WHERE id=?", (m.status, _s(m.read_at), m.id))
        self.conn.commit()

    def for_connection(self, connection_id):
        rows = self.conn.execute("SELECT * FROM messages WHERE connection_id=? ORDER BY sent_at, id",
                                 (connection_id,)).fetchall()
        return [self._row(r) for r in rows]

    def unread_count(self, connection_id, reader_id):
        return self.conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE connection_id=? AND sender_id != ? AND read_at IS NULL "
            "AND status='visible'", (connection_id, reader_id)).fetchone()["c"]

    def mark_read(self, connection_id, reader_id, now):
        self.conn.execute("UPDATE messages SET read_at=? WHERE connection_id=? AND sender_id != ? AND read_at IS NULL",
                          (_s(now), connection_id, reader_id))
        self.conn.commit()

    def last_sent_at(self, connection_id):
        r = self.conn.execute("SELECT MAX(sent_at) m FROM messages WHERE connection_id=?", (connection_id,)).fetchone()
        return _dt(r["m"]) if r and r["m"] else None

    def purge_before(self, cutoff, keep_ids):
        rows = self.conn.execute("SELECT id FROM messages WHERE sent_at < ?", (_s(cutoff),)).fetchall()
        doomed = [r["id"] for r in rows if r["id"] not in keep_ids]
        self.conn.executemany("DELETE FROM messages WHERE id=?", [(i,) for i in doomed])
        self.conn.commit()
        return len(doomed)
