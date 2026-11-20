# Test report

Results of the final run on `main` before submission (18 November 2026, after the final changes).

| Suite | Tool | Tests | Result |
|---|---|---|---|
| Backend (Flask API, services, repositories) | pytest | 180 | all passed (146 before the 20 November review; 15 added by the SRS pass, 14 by the diagram alignment, 5 by the interest suggestions, community names and moderator context) |
| Frontend (Angular services, routes, app shell) | Karma and Jasmine, headless Chrome | 32 | all passed |
| Production build | `ng build` | n/a | succeeds |

Run them with `pytest` in `backend` and `npm test` in `frontend`.

## Backend tests by area

| File | Tests | What it covers |
|---|---|---|
| `test_auth_api.py` | 19 | registration with the conduct notice, verification link, resend limit, sign-in, lockout, session idle expiry |
| `test_connections_api.py` | 22 | requests, accept and decline, wait after decline, suggestions, withdraw and remove, notifications |
| `test_communities.py` | 15 | course and interest communities, posts, replies, edit window, hiding, search |
| `test_moderation.py` | 19 | reports, queue, acknowledgement, decisions, actions, append-only log, role checks |
| `test_admin.py` | 11 | courses, CSV import, domains, communities, moderators, settings, status |
| `test_pilot.py` | 11 | onboarding question, report figures (hand-calculated), small-group merge, CSV without names |
| `test_messaging.py` | 8 | messages between accepted connections, limits, unread counts, retention |
| `test_profiles.py` | 8 | profile rules, public view, account deletion |
| `test_repositories.py`, `test_models.py`, `test_settings.py` | 21 | uniqueness, model rules, settings defaults and limits |
| `test_email_gateway.py` | 5 | stub and live gateway selection, failure handling |
| `test_scaffolding.py`, `test_health.py`, `test_seed.py` | 7 | app set-up, health check, demo seed |
| `test_m3_alignment.py` (20 November diagram alignment) | 14 | related item on every notification (DR-011), `may_access` (NFR-013, IF-004), `respond` route, escalation choice and case summary (DF-23, DF-36, DF-24), later note (DF-25), email choice in the profile (DF-06), `Community.created_at`, `SystemSetting`, `AuditRecord`, enumerations, schema migration |
| `test_review_fixes.py` (20 November review) | 15 | HTTPS enforcement and secret-key guard (IF-006), TLS floor on the email leg (NFR-010), plain error messages and duplicate-safe repeat of a post (NFR-008), database integrity rules (DR-007, DR-009, DR-011), retention clean-up for messages and conduct records (OR-001, OR-002) |

## What is not covered by automated tests

- Live email through the RIT mail server (IF-003): only the stub gateway is tested.
- Angular components are checked through their services and by hand; there are no browser end-to-end tests.
- Response-time targets were not measured under load.
- The retention clean-up is tested (`test_review_fixes.py`, 20 November) and runs on demand (`POST /api/admin/clean-up` or `flask --app app clean-up`); the daily schedule itself is a host job and is not in the code.

See `docs/requirements-coverage.md` for the per-requirement view.
