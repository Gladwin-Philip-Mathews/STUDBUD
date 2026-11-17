# API reference

All endpoints are under `/api` and return JSON. Sessions use a signed cookie; the backend decides who is signed in (NFR-013).

## Auth (process 1.0)
| Method and path | Body | Result |
|---|---|---|
| POST `/api/auth/register` | email, displayName, password | 202 same message for new and existing addresses (FR-004); 400 with `errors` per field (FR-002, FR-003) |
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
| POST `/api/connections/{id}/withdraw` | | requester only (FR-046) |
| POST `/api/connections/{id}/remove` | | either student (FR-048) |
| GET `/api/connections/suggestions` | | up to 10, most shared first (FR-040, FR-041) |
| POST `/api/connections/suggestions/{accountId}/dismiss` | | does not return (FR-041) |

## Notifications (process 7.0) — all need sign-in
| Method and path | Body | Result |
|---|---|---|
| GET `/api/notifications` | | newest first, with unread count (FR-083) |
| GET `/api/notifications/unread-count` | | for the badge on every page (FR-080) |
| POST `/api/notifications/{id}/read` and `/read-all` | | FR-083 |
| PUT `/api/notifications/settings` | email: true/false | email on or off; in-app stays on (FR-082) |

Emails are handed over after the response is sent (DD-04). A returned email is resent at most 3 times, so at most 4 attempts (FR-084, CH-15).
