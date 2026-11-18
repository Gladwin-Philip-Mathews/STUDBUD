# Test report

Results of the final run on `main` before submission (18 November 2026, after the final changes).

| Suite | Tool | Tests | Result |
|---|---|---|---|
| Backend (Flask API, services, repositories) | pytest | 146 | all passed (about 90 s) |
| Frontend (Angular services, routes, app shell) | Karma and Jasmine, headless Chrome | 25 | all passed |
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

## What is not covered by automated tests

- Live email through the RIT mail server (IF-003): only the stub gateway is tested.
- Angular components are checked through their services and by hand; there are no browser end-to-end tests.
- Response-time targets were not measured under load.
- Scheduled clean-up of old messages and logs (retention): the settings and the retention rule are tested, but no scheduler runs it.

See `docs/requirements-coverage.md` for the per-requirement view.
