-- Onboarding answers (D10) and the anonymous request timing record (FR-091). Processes 8.0 and 9.0.
CREATE TABLE IF NOT EXISTS onboarding_answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
  week INTEGER NOT NULL CHECK (week IN (1, 12)),
  answer TEXT NOT NULL CHECK (answer IN ('0', '1 to 2', '3 to 5', 'more than 5', 'skipped')),
  cohort TEXT NOT NULL,
  answered_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_answer_per_week ON onboarding_answers(account_id, week) WHERE account_id IS NOT NULL;
-- Connection requests keep their timing after an account is deleted, with identities removed (FR-091).
CREATE TABLE IF NOT EXISTS request_timings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sent_at TEXT NOT NULL,
  outcome TEXT NOT NULL,
  outcome_at TEXT NOT NULL,
  requester_cohort TEXT,
  requester_intent TEXT
);
