-- Core tables: accounts, profiles, connections, notifications, settings. Owner: Gladwin
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  display_name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unverified',
  role TEXT NOT NULL DEFAULT 'student',
  failed_sign_ins INTEGER NOT NULL DEFAULT 0,
  first_failed_at TEXT,
  locked_until TEXT,
  last_sign_in_at TEXT,
  email_notifications INTEGER NOT NULL DEFAULT 1,
  notice_accepted_at TEXT,
  verified_at TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verification_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT,
  is_resend INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS profiles (
  account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
  intent TEXT NOT NULL DEFAULT 'both',
  cohort TEXT NOT NULL DEFAULT 'prefer not to say',
  year_of_study INTEGER
);
CREATE TABLE IF NOT EXISTS profile_interests (
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  interest TEXT NOT NULL,
  PRIMARY KEY (account_id, interest)
);
CREATE TABLE IF NOT EXISTS profile_courses (
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  course_code TEXT NOT NULL,
  PRIMARY KEY (account_id, course_code)
);
CREATE TABLE IF NOT EXISTS dismissed_suggestions (
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  dismissed_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  PRIMARY KEY (account_id, dismissed_id)
);
CREATE TABLE IF NOT EXISTS connections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  requester_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
  receiver_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  status_changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recipient_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read_at TEXT,
  email_status TEXT NOT NULL DEFAULT 'not sent',
  email_resends INTEGER NOT NULL DEFAULT 0 CHECK (email_resends BETWEEN 0 AND 3)
);
CREATE TABLE IF NOT EXISTS settings (
  name TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  changed_at TEXT,
  changed_by INTEGER
);
CREATE TABLE IF NOT EXISTS accepted_domains (
  domain TEXT PRIMARY KEY COLLATE NOCASE,
  added_at TEXT,
  added_by INTEGER
);
CREATE TABLE IF NOT EXISTS audit_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  actor_id INTEGER,
  action TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT ''
);
