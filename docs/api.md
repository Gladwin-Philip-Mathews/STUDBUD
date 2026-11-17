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
