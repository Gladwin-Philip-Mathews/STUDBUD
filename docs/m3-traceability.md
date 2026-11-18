# M3 to code traceability

How the code maps to the M3 diagrams (DFD-0, DFD-1, CD-1a/1b, SD-1). Python names use snake_case: `findOpenBetween` is `find_open_between`.
Status: **Done** = built and tested, **Next** = planned before 20 Nov, **Deferred** = see the deferred table (to be added at the end).

## Data stores (DFD-0)

| Store | Diagram name | Table(s) | Status |
|---|---|---|---|
| D1 | Accounts | `accounts`, `verification_tokens` | Done |
| D2 | Profiles | `profiles`, `profile_interests`, `profile_courses`, `dismissed_suggestions` | Done |
| D3 | Courses | `courses` | Table done, admin Next |
| D4 | Communities | `communities` | Next |
| D5 | Posts and replies | `posts`, `replies` | Next |
| D6 | Connections | `connections` | Done |
| D7 | Messages | `messages` | Next |
| D8 | Moderation Log | `safety_reports`, `moderation_outcomes` | Next |
| D9 | Notifications | `notifications` | Done |
| D10 | Onboarding answers | `onboarding_answers` | Next |
| D11 | Settings | `settings`, `accepted_domains` | Done |
| D12 | Audit Record | `audit_records` | Done |

## Processes

| Process | Code | Status |
|---|---|---|
| 1.0 Register and authenticate | `AuthService`, `controllers/auth.py` | Done |
| 2.0 Maintain profile | `ProfileService`, `controllers/profile.py`, `frontend/.../profiles` | Done (FR-010 to 015; FR-022 with communities) |
| 3.0 Communities and posts | `CommunityService` | Next |
| 4.0 Manage connections | `ConnectionService`, `controllers/connections.py` | Done |
| 5.0 Private messages | `MessagingService` | Next |
| 6.0 Safety reports (DFD-1: 6.1 to 6.6) | `ModerationService` (`submit_report`, `open_queue`, `acknowledge`, `decide`, `apply_action`, `case_summary`) | Next |
| 7.0 Notifications | `NotificationService`, `EmailGateway` | Done |
| 8.0 Pilot measures | `PilotMeasuresService` | Next |
| 9.0 Administer system | `AdminService` | Next |

## Classes and operations (CD-1a) and SD-1

| M3 | Code | SD-1 |
|---|---|---|
| `ConnectionService.sendRequest()` | `send_request` | M5 |
| `ConnectionService.checkRequest()` | `check_request` | M14, M15 |
| `ConnectionService.respond()` | `respond` | outside SCN-01 |
| `ConnectionRepository.findOpenBetween()` | `find_open_between` | M8, M9 |
| `ConnectionRepository.lastDeclineBy()` | `last_decline_by` | M10, M11 |
| `AccountRepository.findById()` | `get` | M6, M7 |
| `SettingsProvider.duration()` / `value()` | `duration` / `value` | M12, M13 |
| `NotificationService.notify()` | `notify` | M20 to M23 |
| `NotificationService.dispatchEmail()` | `dispatch_email` | M22, M26 to M31 |
| `NotificationService.onDeliveryStatus()` | `on_delivery_status` | M32 to M35 |
| `EmailGateway`, `StubEmailGateway`, `RitEmailGateway` | `email_gateway/gateway.py` | M26 to M29 |
| `AuditLog.record()` | `services/audit_log.py` | DFD-1 6.2, 6.4 |
| `AuthService.currentAccount()` | `current_account` | M2, M3 |
| `Account.canSignIn()`, `recordFailedSignIn()`, `suspend()` | same, snake_case | |
| `Connection.accept()`, `decline()`, `withdraw()`, `remove()`, `isOpen()` | same, snake_case | |

Controllers are Flask routes under `/api` (`docs/api.md`). `ConnectionController.sendRequest()` is `POST /api/connections`.
