"""SettingsProvider: reads NFR-012 limits at run time so they change without a release."""
from datetime import datetime, timezone

from .models.enums import SettingName

DEFAULTS = {
    SettingName.VERIFICATION_LINK_LIFE: 24,
    SettingName.RESEND_LIMIT: 3,
    SettingName.LOCKOUT_ATTEMPTS: 5,
    SettingName.LOCKOUT_WINDOW: 15,
    SettingName.LOCKOUT_PERIOD: 15,
    SettingName.OVERDUE_FLAG: 36,
    SettingName.REQUEST_DECLINE_WAIT: 30,
    SettingName.SESSION_IDLE_TIME: 2,
}


class SettingsProvider:
    def __init__(self, conn):
        self.conn = conn

    def get(self, name: SettingName) -> int:
        name = SettingName(name)
        row = self.conn.execute("SELECT value FROM settings WHERE name = ?", (name.value,)).fetchone()
        if row is not None:
            return int(row["value"])
        return DEFAULTS[name]

    def set(self, name, value: int, changed_by=None) -> None:
        # DR-014: a name outside the NFR-012 list cannot be stored
        name = SettingName(name)
        self.conn.execute(
            "INSERT INTO settings(name, value, changed_at, changed_by) VALUES (?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET value=excluded.value, changed_at=excluded.changed_at, "
            "changed_by=excluded.changed_by",
            (name.value, str(int(value)), datetime.now(timezone.utc).isoformat(), changed_by),
        )
        self.conn.commit()
