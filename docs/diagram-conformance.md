# Diagram conformance review

The built system was checked against the M1 context diagram and domain model, DFD-0, DFD-1 (child of 6.0), CD-1a,
CD-1b and SD-1 as issued in M3 v1.0. First pass on 18 November 2026; second pass on 20 November 2026, element by
element against the figures and the tables of M3 sections 2.3, 3.2 and 4.3, after which every code-side difference
was closed. What remains below are differences in the figures themselves, which belong in the M3 change record.

## Result

| Diagram | Result |
|---|---|
| M1 context diagram (F-01 to F-12) | Matches. Five external entities; F-11 and F-12 (Student Affairs) are proposed in M1 and M3 and are implemented as the case summary endpoint and the later note, both operated by a moderator rather than by a Student Affairs account. |
| M1 domain model | Matches, with the M2 additions already recorded as RV-03 (connection statuses withdrawn and removed). |
| DFD-0 | Nine processes and stores D1 to D12 match. One email route through 7.0. Account deletion (2.0) writes to D2, D6, D7 and D9, and D6 keeps anonymised request timing. The email notification choice travels in DF-06 (`PUT /api/profile`, process 2.0) as the diagram says, as well as on the notifications page. |
| DFD-1 | 6.1 to 6.6 are `submit_report`, `open_queue`, `acknowledge`, `decide`, `apply_action`, `case_summary`. DF-23 carries the escalation choice (upheld only); 6.4 passes DF-36 to 6.6 and returns DF-24 with the outcome. DF-25 is recorded by 6.4 as a later note. Message access (6.2) and decisions (6.4) are written to D12 with the item reference kept apart from the detail. |
| CD-1a | All 17 entity classes are present with their attributes and operations: `AuditRecord` and `SystemSetting` are entity classes, `Community.created_at` exists, `Notification.related_item` holds the DR-011 item. `ItemRef` is the datatype behind `relatedItem`, `itemRef` and `mayAccess(item)`. |
| CD-1b | Every operation in the figure has a code counterpart (table below), including `AuthService.may_access()`, `ConnectionController.respond()`, `StubEmailGateway.sent_messages()`, `EmailMessage.notification_id` and `HandoffResult`. The five enumerations of section 3.2 that were plain strings are enumeration types. |
| SD-1 (M1 to M35) | The call order in `send_request` matches: session check, receiver lookup, open connection, last decline, decline wait, `check_request`, create, save, notify with the connection as item, asynchronous email. M30 and M31 now behave as drawn: an unavailable route leaves the status "not sent" and the handoff is retried; only a returned message (M32 to M35) counts towards the three resends. |

## CD-1b operations and their code

| CD-1b | Code |
|---|---|
| `ConnectionController.sendRequest()`, `respond()` | `POST /api/connections/requests`, `POST /api/connections/{id}/respond` (`accept` and `decline` routes kept) |
| `ModerationController.submitReport()`, `showQueue()`, `acknowledge()`, `decide()` | `POST /api/reports`, `GET /api/moderation/queue`, `POST .../acknowledge`, `POST .../decision` |
| `AuthService.register()`, `verify()`, `signIn()`, `currentAccount()`, `mayAccess()` | `register`, `verify`, `sign_in`, `current_account`, `may_access` |
| `ConnectionService.sendRequest()`, `respond()`, `withdraw()`, `suggestions()`, `checkRequest()` | same names in snake_case |
| `ModerationService.submitReport()`, `openQueue()`, `acknowledge()`, `decide()`, `caseSummary()`, `applyAction()` | same names in snake_case; `decide(..., escalate)` |
| `NotificationService.notify(recipient, type, item)`, `onDeliveryStatus()`, `dispatchEmail()` | `notify(recipient_id, event, body, item)`, `on_delivery_status`, `dispatch_email` |
| `SettingsProvider.duration()`, `value()` | same |
| `AuditLog.record(actor, action, item)` | `record(actor_id, action, item, detail)` |
| `ConnectionRepository.findOpenBetween()`, `lastDeclineBy()`, `save()` | `find_open_between`, `last_decline_by`, `add` / `save` |
| `AccountRepository.findById()`, `save()`; `ReportRepository.findOpen()`, `save()`; `NotificationRepository.save()`, `findById()` | `get`, `save`; `find_open`, `save`; `save`, `get` |
| `EmailGateway.send(message): HandoffResult`; `RitEmailGateway`; `StubEmailGateway.sentMessages()` | `send` returns `HandoffResult.HANDED_OVER` or `UNAVAILABLE`; `sent_messages()` |
| `RequestResult`, `RefusalReason`, `EmailMessage {to, subject, body, notificationId}` | same, `notification_id` |
| "Other feature services": `ProfileService`, `CommunityService`, `MessagingService`, `PilotMeasuresService`, `AdminService` | same class names |

The security decorators are the controller side of `mayAccess()`: `page_required("moderation")` and
`page_required("admin")` call `AuthService.may_access(account, ItemRef("page", ...))` (IF-004), and the conversation and
notification routes call it with the item (NFR-013).

## Remaining differences (in the figures, not the code)

| Item | Diagram | Code | Decision |
|---|---|---|---|
| `Account.firstFailedAt` | not shown | present | Needed for the 15 minute window of FR-009. Add to CD-1a. |
| `Course.title` | `title` | `name` internally; the API and pages say title | Naming only; no behaviour depends on it. |
| DFD-0 input "decline wait" | drawn from D11 into 3.0 | used by `ConnectionService` (4.0), as SD-1 M12 and the M3 text say | The diagram arrow is misplaced. Fix the figure. |
| DFD-0 process 8.0 | no flow from D1 | active users use the last sign-in time in D1 (FR-092, CH-15) | A flow D1 to 8.0 is missing from the figure. |
| D11 Settings | holds accepted domains and settings | two tables, `settings` and `accepted_domains` | Internal partition of one store. |
| Retention clean-up | 5.0 "applies message retention"; no process owns OR-002 | `RetentionService` applies OR-001 and OR-002 on demand and from the shell | Allocate OR-002 to 9.0 (or a note under 6.0) in the next M3 revision. |
| Cover of the M3 PDF | "ikwncGladwin Mathews" | | Typo in the document. |
