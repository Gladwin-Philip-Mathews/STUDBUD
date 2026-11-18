"""SettingsProvider: reads NFR-012 limits at run time so they change without a release."""
from datetime import datetime, timedelta, timezone

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
    SettingName.MESSAGE_RETENTION: 120,  # days: end of the pilot plus 30 days (OR-001, CH-15)
    SettingName.LOG_RETENTION: 365,  # days (OR-002, CH-15)
}


# Unit of each stored number, so callers ask for a duration and never do the arithmetic (SD-1 M12, M13)
UNITS = {
    SettingName.VERIFICATION_LINK_LIFE: "hours",
    SettingName.OVERDUE_FLAG: "hours",
    SettingName.SESSION_IDLE_TIME: "hours",
    SettingName.LOCKOUT_WINDOW: "minutes",
    SettingName.LOCKOUT_PERIOD: "minutes",
    SettingName.REQUEST_DECLINE_WAIT: "days",
    SettingName.MESSAGE_RETENTION: "days",
    SettingName.LOG_RETENTION: "days",
}


class SettingsProvider:
    def __init__(self, conn):
        self.conn = conn

    def value(self, name: SettingName) -> int:
        """CD-1a SettingsProvider.value(): the stored number."""
        return self.get(name)

    def duration(self, name: SettingName) -> timedelta:
        """CD-1a SettingsProvider.duration(): the setting as a time span."""
        name = SettingName(name)
        return timedelta(**{UNITS[name]: self.get(name)})

    def get(self, name: SettingName) -> int:
        name = SettingName(name)
        row = self.conn.execute("SELECT value FROM settings WHERE name = ?", (name.value,)).fetchone()
        if row is not None:
            return int(row["value"])
        return DEFAULTS[name]

    def all(self) -> list:
        """Every setting with its value and unit, for the administration page (FR-104)."""
        return [{"name": n.value, "value": self.get(n), "unit": UNITS.get(n, "count")} for n in SettingName]

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
