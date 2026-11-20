-- Moderation Log (D8): reports, their single outcome and dated later notes. Process 6.0 (DFD-1).
CREATE TABLE IF NOT EXISTS safety_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reporter_id INTEGER NOT NULL REFERENCES accounts(id),
  reported_student_id INTEGER NOT NULL REFERENCES accounts(id),
  item_type TEXT NOT NULL CHECK (item_type IN ('student', 'post', 'reply', 'message')),
  item_id INTEGER,
  reason TEXT NOT NULL,
  text TEXT NOT NULL DEFAULT '',
  received_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'closed')),
  acknowledged_at TEXT,
  acknowledged_by INTEGER REFERENCES accounts(id),
  CHECK (reporter_id != reported_student_id)
);
CREATE TABLE IF NOT EXISTS moderation_outcomes (
  report_id INTEGER PRIMARY KEY REFERENCES safety_reports(id),
  decision TEXT NOT NULL CHECK (decision IN ('upheld', 'dismissed')),
  action TEXT NOT NULL CHECK (action IN ('none', 'warning', 'content hidden', 'account suspended')),
  note TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  moderator_id INTEGER NOT NULL REFERENCES accounts(id)
);
CREATE TABLE IF NOT EXISTS outcome_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL REFERENCES moderation_outcomes(report_id),
  note TEXT NOT NULL,
  added_at TEXT NOT NULL,
  moderator_id INTEGER NOT NULL REFERENCES accounts(id)
);
-- DR-009: a report with a reason outside the five reasons cannot be stored.
CREATE TRIGGER IF NOT EXISTS reports_reason_check BEFORE INSERT ON safety_reports
WHEN NEW.reason NOT IN ('harassment', 'spam', 'unsafe or inappropriate content', 'academic integrity', 'other')
BEGIN SELECT RAISE(ABORT, 'report reason is not one of the listed reasons (DR-009)'); END;
-- The log is append-only: no role can change or remove an outcome or a note (FR-067, DR-010).
-- The one exception is the retention clean-up (OR-002), which runs as the system, not as a role: it inserts a row
-- into retention_unlock inside its transaction, deletes the expired entries, and removes the row again.
CREATE TABLE IF NOT EXISTS retention_unlock (id INTEGER PRIMARY KEY CHECK (id = 1));
CREATE TRIGGER IF NOT EXISTS outcomes_no_update BEFORE UPDATE ON moderation_outcomes
BEGIN SELECT RAISE(ABORT, 'moderation outcomes cannot be changed'); END;
DROP TRIGGER IF EXISTS outcomes_no_delete;
CREATE TRIGGER outcomes_no_delete BEFORE DELETE ON moderation_outcomes
WHEN (SELECT COUNT(*) FROM retention_unlock) = 0
BEGIN SELECT RAISE(ABORT, 'moderation outcomes cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS notes_no_update BEFORE UPDATE ON outcome_notes
BEGIN SELECT RAISE(ABORT, 'notes cannot be changed'); END;
DROP TRIGGER IF EXISTS notes_no_delete;
CREATE TRIGGER notes_no_delete BEFORE DELETE ON outcome_notes
WHEN (SELECT COUNT(*) FROM retention_unlock) = 0
BEGIN SELECT RAISE(ABORT, 'notes cannot be deleted'); END;
