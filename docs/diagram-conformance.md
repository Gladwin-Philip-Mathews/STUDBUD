# Diagram conformance review

The built system was checked against the M1 context diagram, DFD-0, DFD-1 (child of 6.0), CD-1a, CD-1b and SD-1 as issued in M3 v1.0, on 18 November 2026.

## Result

| Diagram | Result |
|---|---|
| Context diagram (F-01 to F-12) | Matches. Five external entities; F-11 and F-12 stay proposed and have no code. |
| DFD-0 | Nine processes and stores D1 to D12 match. One email route through 7.0. Account deletion writes to D2, D6, D7 and D9, and D6 keeps anonymised request timing. |
| DFD-1 | 6.1 to 6.6 match `submit_report`, `open_queue`, `acknowledge`, `decide`, `apply_action`, `case_summary`. Message access (6.2) and decisions (6.4) are written to the audit record. DF-24 and DF-25 stay proposed. |
| CD-1a | All entities, associations and operations are present, with the differences below. |
| CD-1b | Controllers, services, repositories, `EmailGateway` with its two implementations and `RefusalReason` match, with the differences below. |
| SD-1 (M1 to M35) | The call order in `send_request` matches: session check, receiver lookup, open connection, last decline, decline wait, `check_request`, create, save, notify, asynchronous email, delivery status with at most 3 resends. |

## Differences between diagrams and code

| Item | Diagram | Code | Decision |
|---|---|---|---|
| `Account.verifiedAt` | present | missing until this branch | Added (`verified_at`, set on verification). |
| `Account.isActiveStudent()` | present | missing until this branch | Added. |
| Sign-ins by a moderator or administrator | NFR-015 requires them in the audit record | not recorded until this branch | Added (`SIGN_IN` entry). |
| `Account.firstFailedAt` | not shown | present | Needed for the 15 minute window of FR-009. The diagram is incomplete. |
| `Course.title` | `title` | `name` (the API and pages say title) | Internal name only. |
| `AuditRecord` | actor, action, itemRef, at | `actor_id`, `action`, `detail` (item and detail joined), `at` | Same content in one text field. |
| `EmailGateway.send()` | returns `HandoffResult` (accepted or unavailable); an unavailable route leaves the status "not sent" and is retried | returns true or false; false is stored as "returned" and counts as a resend | Open deviation. In the pilot with the stub the two behave the same. |
| `StubEmailGateway.sentMessages()` | operation | `sent` list | Naming only. |
| DFD-0 input "decline wait" | drawn from D11 into 3.0 | used by `ConnectionService` (4.0), as SD-1 M12 and the M3 text say | The diagram arrow is misplaced. Fix the figure. |
| DFD-0 process 8.0 | no flow from D1 | active users use the last sign-in time in D1 (FR-092, CH-15) | A flow D1 to 8.0 is missing from the figure. |
| M1 domain model | connection status pending, accepted, declined | adds withdrawn and removed (M2 DR-007) | Already recorded as RV-03. |
