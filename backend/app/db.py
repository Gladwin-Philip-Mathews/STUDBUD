"""SQLite connection and schema loader. Dates are stored as ISO-8601 UTC text."""
import sqlite3
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent / "schema"



DEFAULT_DOMAINS = ("rit.edu", "g.rit.edu", "mail.rit.edu")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    # Every feature adds its own file in app/schema/ (NN_feature.sql). Files run in name order.
    for sql_file in sorted(SCHEMA_DIR.glob("*.sql")):
        conn.executescript(sql_file.read_text(encoding="utf-8"))
    # Databases made before DR-013 lack the "added" columns; add them once.
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(accepted_domains)")}
    for column, kind in (("added_at", "TEXT"), ("added_by", "INTEGER")):
        if column not in columns:
            conn.execute(f"ALTER TABLE accepted_domains ADD COLUMN {column} {kind}")
    if "notice_accepted_at" not in {r["name"] for r in conn.execute("PRAGMA table_info(accounts)")}:
        conn.execute("ALTER TABLE accounts ADD COLUMN notice_accepted_at TEXT")  # OR-003
    for d in DEFAULT_DOMAINS:
        conn.execute("INSERT OR IGNORE INTO accepted_domains(domain) VALUES (?)", (d,))
    conn.commit()
