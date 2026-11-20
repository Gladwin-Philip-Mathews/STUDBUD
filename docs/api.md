# API reference

All endpoints are under `/api` and return JSON. Sessions use a signed cookie; the backend decides who is signed in (NFR-013).

## Auth (process 1.0)
| Method and path | Body | Result |
|---|---|---|
| POST `/api/auth/register` | email, displayName, password, acceptNotice (must be true, OR-003) | 202 same message for new and existing addresses (FR-004); 400 with `errors` per field (FR-002, FR-003) |
| POST `/api/auth/verify` | token | 200 verified; 400 invalid, expired or used (FR-005, FR-006) |
| POST `/api/auth/resend` | email | 202; 429 after 3 per hour (FR-006) |
| POST `/api/auth/sign-in` | email, password | 200 and session; 401 one message for wrong email or password (FR-008); 403 unverified (FR-007) or suspended; 429 locked (FR-009) |
| POST `/api/auth/sign-out` | | 200 |
| GET `/api/auth/me` | | 200 account; 401 when signed out, idle over 2 hours, or suspended (NFR-011, FR-066) |
| GET `/api/health` | | 200 `{status: ok}` |

## Connections (process 4.0, SD-1) — all need sign-in
| Method and path | Body | Result |
|---|---|---|
| POST `/api/connections/requests` | receiverId, note (max 200) | 201 pending request; 400 with `reason` (NOTE_TOO_LONG, SELF, NOT_AVAILABLE, ALREADY_CONNECTED, PENDING_EXISTS, RECENTLY_DECLINED). The text never says "declined" (FR-043) |
| GET `/api/connections` | | accepted connections with shared courses and interests (FR-047) |
| GET `/api/connections/incoming` and `/outgoing` | | pending requests |
| POST `/api/connections/{id}/accept` or `/decline` | | receiver only (FR-044, FR-045) |
| POST `/api/connections/{id}/respond` | accept: true/false | the same two answers in one route (CD-1b `ConnectionController.respond()`) |
| POST `/api/connections/{id}/withdraw` | | requester only (FR-046) |
| POST `/api/connections/{id}/remove` | | either student (FR-048) |
| GET `/api/connections/suggestions` | | up to 10, most shared first (FR-040, FR-041) |
| POST `/api/connections/suggestions/{accountId}/dismiss` | | does not return (FR-041) |

## Notifications (process 7.0) — all need sign-in
| Method and path | Body | Result |
|---|---|---|
| GET `/api/notifications` | | newest first, with unread count (FR-083), the email choice (FR-082) and, per notification, `item: {type, id}`: the post, connection, conversation or report it is about (DR-011) |
| GET `/api/notifications/unread-count` | | for the badge on every page (FR-080) |
| POST `/api/notifications/{id}/read` and `/read-all` | | FR-083 |
| PUT `/api/notifications/settings` | email: true/false | email on or off; in-app stays on (FR-082) |

Emails are handed over after the response is sent (DD-04). A returned email is resent at most 3 times, so at most 4 attempts (FR-084, CH-15).

## Moderation (process 6.0, DFD-1) — moderator role only, except the report itself
| Method and path | Body | Result |
|---|---|---|
| POST `/api/reports` | itemType, itemId, reason, text | 201 with `reportId` (6.1, FR-060, FR-061); 400 per field (FR-069) |
| GET `/api/moderation/queue` | | open reports oldest first with age, overdue flag and the reported item; each message access is audited (6.2, FR-054, FR-062) |
| POST `/api/moderation/reports/{id}/acknowledge` | | 6.3, FR-063; a second acknowledgement changes nothing |
| POST `/api/moderation/reports/{id}/decision` | decision, action, note, escalate (optional, upheld only) | 6.4, FR-064 to FR-068; with `escalate` the response carries `caseSummary` (DF-36 to 6.6, DF-24) |
| POST `/api/moderation/reports/{id}/notes` | note | dated later note on a closed report, the only permitted change (FR-067); how a conduct decision from Student Affairs is recorded (DF-25) |
| GET `/api/moderation/reports/{id}/summary` | | case summary of an upheld report, reported item only (6.6, FR-070) |

## Profile (process 2.0) — sign-in required
`GET`/`PUT /api/profile` carry intent, cohort, year of study, interests, courses and `emailNotifications` (DF-06: the
email choice of FR-082 is part of the profile details); `DELETE /api/profile` with the password deletes the account (FR-015).

## Administration (process 9.0) — administrator role only
Courses, accepted domains, interest communities, moderators, settings and the pilot report are under `/api/admin`
(see `backend/app/controllers/admin.py`). Added by the 20 November review:

| Method and path | Body | Result |
|---|---|---|
| POST `/api/admin/clean-up` | | runs the retention rules now: messages older than MESSAGE_RETENTION unless an open or recent report names them (OR-001); closed reports with their outcome and notes, and audit entries, older than LOG_RETENTION (OR-002). Returns the counts and writes one audit entry. The same run is `flask --app app clean-up` for a daily job |

## Errors (NFR-008, IF-002, NFR-021)
Every failure under `/api` is JSON with a plain `message` that names the next step; validation failures carry
`errors` keyed by field. A server error returns 500 with a fixed message and no technical detail; the request's
database work is not committed, so repeating the action is safe. Repeating an identical post within 5 minutes returns
the stored post with 200 instead of creating a second one.

## Transport (IF-006, NFR-010)
With `FORCE_HTTPS=1` a GET on the plain HTTP address is redirected (308) to HTTPS, other methods are refused (403), the
session cookie is `Secure` and `HttpOnly`, and `Strict-Transport-Security` is sent. The email leg uses TLS 1.2 or later.
