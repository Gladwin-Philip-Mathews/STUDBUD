import pytest

from app.models.enums import SettingName
from app.settings import SettingsProvider


def test_defaults_match_nfr_012(conn):
    s = SettingsProvider(conn)
    assert s.get(SettingName.VERIFICATION_LINK_LIFE) == 24
    assert s.get(SettingName.LOCKOUT_ATTEMPTS) == 5
    assert s.get(SettingName.OVERDUE_FLAG) == 36
    assert s.get(SettingName.REQUEST_DECLINE_WAIT) == 30
    assert s.get(SettingName.SESSION_IDLE_TIME) == 2


def test_changed_setting_applies_without_release(conn):  # AC-NFR-012a
    s = SettingsProvider(conn)
    s.set(SettingName.OVERDUE_FLAG, 24)
    assert s.get(SettingName.OVERDUE_FLAG) == 24


def test_unknown_setting_cannot_be_stored(conn):  # AC-DR-014a
    with pytest.raises(ValueError):
        SettingsProvider(conn).set("NOT_A_SETTING", 1)
