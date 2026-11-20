# Implementation review against the M2 SRS and the M3 design

Date: 20 November 2026. Baseline reviewed: `main` as of the 20-commit zip (last commit "Add global styling based on
the RIT brand colours", c7402d4). Documents used: `SWEN261_Team02_M2_SRS_v1.0` (132 requirements, baselined 25
October) and `SWEN261_Team01_M3_DesignDescription_v1.0` (31 October).

## Verdict

The implementation is in good shape. All 71 functional requirements that the SRS commits to release 1 are present
with an acceptance test named after the AC or TC, the M3 layering is respected throughout, and the SRS rules that
matter most for the three goals (consent-based connections with the 30-day wait, the 36-hour overdue flag, the
append-only Moderation Log, the pilot report with the hand-calculated figures) are implemented and tested. 146
backend and 25 frontend tests passed before this review.

The gaps were in the non-functional and data requirements that the team's own coverage document did not list:
36 of the 132 IDs had no row. Most of those are load, usability or process checks that belong to the pilot (NFR-001,
NFR-003, NFR-020, OR-004) and cannot be closed in code. Eight could be, and are now (section 2). Everything the SRS
defers or excludes is still absent, as it should be (section 4).

After the changes: 175 backend tests and 28 frontend tests pass; `ng build` succeeds (initial bundle 342 kB raw,
94 kB transferred, inside NFR-022's 1.5 MB). Section 6 covers the second pass, in which the code was aligned element
by element with the M1 and M3 figures.

## 1. Method

1. Ran the test suites and the build.
2. Extracted the 132 requirement IDs from the SRS and compared them with the IDs cited in code comments, test names
   and `docs/requirements-coverage.md`.
3. Read every service, the schema, the app factory, the email gateway and the core-flow Angular templates against
   the requirement statements and acceptance criteria.
4. Checked the code structure against CD-1 (boundary controllers, control services, entities, repositories behind
   interfaces, one EmailGateway) and SD-1 (the fixed order of refusal rules in `ConnectionService.check_request`).
5. Fixed what could be fixed in code, with a test per acceptance criterion, and recorded what cannot.

## 2. Findings that were fixed

| # | ID | Priority | Was | Now | Where | Test |
|---|---|---|---|---|---|---|
| 1 | OR-001, OR-002 | Must | `MessagingService.apply_retention` existed but **nothing called it**; no clean-up for the Moderation Log or audit record at all. The `MESSAGE_RETENTION` and `LOG_RETENTION` settings had no effect. The append-only triggers also made OR-002's deletion impossible. | `RetentionService.run()` applies both rules, reachable as `POST /api/admin/clean-up` (administrator, audited) and `flask --app app clean-up` for a daily host job. Closed reports older than LOG_RETENTION are removed with their outcome and notes; open reports never are. The append-only triggers (FR-067) stand down only while a `retention_unlock` row exists inside the clean-up transaction, so no role can delete an outcome by hand. | `services/retention_service.py`, `repositories/report_repo.py`, `services/audit_log.py`, `controllers/admin.py`, `__init__.py`, `schema/40_moderation.sql` | TC-OR-001a (via the run), TC-OR-002a, open-report guard, CLI, role check |
| 2 | IF-006, NFR-010 | Must | No HTTPS enforcement, no HSTS, session cookie not marked `Secure`, `SECRET_KEY` defaulted to `dev` with nothing stopping that reaching a server. SMTP `starttls()` accepted any TLS version. | `FORCE_HTTPS=1` redirects plain HTTP (308 for GET, 403 otherwise, `X-Forwarded-Proto` honoured), sends HSTS, sets `SESSION_COOKIE_SECURE`; `SESSION_COOKIE_HTTPONLY` is always on; the server refuses to start in HTTPS mode with a placeholder key. The email leg uses an SSL context with TLS 1.2 as the floor. Off by default so the laptop setup is unchanged. | `__init__.py`, `email_gateway/gateway.py`, `.env.example`, `README.md` | TC-IF-006a, TC-NFR-010a, secret-key guard |
| 3 | NFR-008 | Must | A server error returned Flask's HTML page (a traceback in debug mode); a repeated submission after a failure created a second post. | JSON error handlers for 404, 405, 413, 429 and 500 with plain messages that name the next step (also IF-002, NFR-021). An identical post by the same author in the same community within 5 minutes returns the stored post (200) instead of a duplicate. | `__init__.py`, `services/community_service.py`, `repositories/community_repo.py`, `controllers/communities.py` | TC-NFR-008a (both halves), boundary test |
| 4 | DR-007 | Must | "One open connection per pair" was enforced only in `ConnectionService`; a double submit racing the check could store two rows. | Partial unique index on the ordered pair where status is pending or accepted. | `schema/00_core.sql` | TC-DR-007a |
| 5 | DR-009 | Must | Report reason validated in the service only. | `BEFORE INSERT` trigger refuses a reason outside the five listed. | `schema/40_moderation.sql` | TC-DR-009a |
| 6 | DR-011 | Must | Notification event type validated in the service only; AC-DR-011a ("cannot be stored") was not met at the store. | `BEFORE INSERT` trigger refuses an event type outside the six events. | `schema/00_core.sql` | TC-DR-011a |
| 7 | NFR-019 | Must | Posting, replying, messaging, connection notes and the report form relied on `placeholder` for their names (WCAG 2.1 SC 1.3.1 and 3.3.2 failures); errors and confirmations were not announced to a screen reader. Registration, sign-in and profile were already labelled. | `aria-label` on every control that has no visible `<label>`; `role="alert"` on error messages and `role="status"` on confirmations; `aria-invalid` and `aria-describedby` on the registration fields. | 13 Angular templates | Checked by hand and by `ng build`/`ng test`; the automated checker and the screen-reader run in AC-NFR-019a remain to do |
| 8 | CON-002 | Must | Already clean (no third-party script, font or tracker); the finding is that it was undocumented. | `Referrer-Policy: same-origin` and `X-Content-Type-Options: nosniff` added; row added to the coverage document. | `__init__.py`, `docs/requirements-coverage.md` | Inspection |

Triggers rather than `CHECK` constraints were used for 5 and 6 because `CREATE TABLE IF NOT EXISTS` does not alter an
existing database; a trigger with `IF NOT EXISTS` protects databases created before this review as well.

## 3. Findings confirmed correct (no change)

| Area | What was checked | Result |
|---|---|---|
| FR-001 to FR-009 | RIT-domain check from the accepted-domains table (CON-004, FR-101), 24-hour single-use token stored as a hash (NFR-009), resend limit, same message for wrong password and unknown email, lock-out with controlled clock, 2-hour idle session | Correct |
| FR-040 to FR-048, SD-1 | Refusal rules in the fixed order of SD-1 (note length, self, availability, open connection, recent decline); RECENTLY_DECLINED and NOT_AVAILABLE read the same to the student (DD-11); 30-day wait from the setting | Correct |
| FR-060 to FR-070 | Queue oldest first with the overdue flag from OVERDUE_FLAG; acknowledgement stores time and notifies; decision requires decision, action and note; dismissed cannot carry an action; outcome insert-only with dated later notes; message text visible to a moderator only through a report and audited (FR-054); case summary only for upheld reports and without other messages | Correct |
| FR-090 to FR-094, NFR-024 | Onboarding question in week 1 and week 12; acceptance within 7 days, acknowledgement within 48 hours, upheld per 100 active users (signed in within 7 days, SRS 1.3); hand-calculated data set in `test_report_figures_match_the_hand_calculation` matches AC-FR-092a (60 %, 87.5 %, 2.5 per 100); groups under 5 merged; CSV without names | Correct |
| CON-009, DD-03 | One `EmailGateway`; stub unless `EMAIL_MODE=live` and `SMTP_HOST` are set; email handed over after the response (DD-04); returned mail resent at most 3 times | Correct |
| NFR-012, DR-014 | Every team-proposed limit is a `SettingName` read at run time; unknown names refused | Correct |
| NFR-013 | `login_required`, `profile_required`, `role_required` on the server for every route; conversations and notifications filtered by account | Correct |
| M3 CD-1 / DD-10 | Controllers translate only; rules in services and entities; persistence behind repository interfaces with SQLite implementations; `SettingsProvider.value()/duration()` as in CD-1a | Conforms |
| Deferred and excluded | FR-016, FR-026, FR-049, NFR-017 absent (documented in `docs/deferred-requirements.md`); no anonymous posting, no other-university domains, no university-system integration, web only | Conforms |

## 4. Still open after this review

These cannot be closed in the repository; they are pilot or hosting tasks and should stay on the team's list.

| ID | What remains | Owner (per SRS) |
|---|---|---|
| NFR-001, NFR-003 | Load test: 100 simulated students for 10 minutes on a 4 Mbit/s link; capacity message at 500 accounts | Team, before the pilot |
| NFR-006, NFR-007 | Uptime log and a daily backup with one rehearsed restore; both depend on the host (Q-04) | Ruslan (Q-04) |
| NFR-019 | Automated accessibility check and one keyboard-only and screen-reader run of the eight core flows (AC-NFR-019a) | Team, planned peer test |
| NFR-020 | Usability test with 5 students (needs the running prototype) | Team (OI-06) |
| IF-005, NFR-018 | Acceptance script on the nine browser and device combinations at 360 px and 1920 px | Team |
| IF-003, CON-009 | Live email route untested until IT services approve the prototype; the stub prints links to the backend console meanwhile | Ruslan (Q-04) |
| OR-002 | The 12-month period is the team's proposal; Student Affairs may set another (Q-05). It is a setting, so no release is needed | Gladwin (Q-05) |
| OR-004 | The invited-student list before the first registration; no public link | Gladwin (Q-01) |
| Retention schedule | `flask --app app clean-up` must be scheduled daily on the pilot host (cron or equivalent); the code provides the run, not the timer | Whoever sets up the host |

## 5. Small things noticed on the way (first pass)

- `docs/test-report.md` said the backend suite takes about 90 s; it takes about 20 s here. Updated to the new count.
- The repository is named Team02 in the SRS and Team01 / Group 1 in the M3 document and the slides. Harmless, but the
  cover of the submitted M3 PDF also reads "ikwncGladwin Mathews"; worth fixing in the `.docx` if it is resubmitted.
- `README.md` still says "Confirm at the first team meeting; see M3-Q-01" about the stack. The stack is decided (Angular
  20, Flask, SQLite); the note can go.

## 6. Second pass: alignment with the submitted diagrams (20 November, afternoon)

Every figure in the submitted documents was read against the code: the M1 context diagram (F-01 to F-12) and domain
model, DFD-0 (nine processes, D1 to D12, DF-01 to DF-34), DFD-1 (6.1 to 6.6, DF-35, DF-36), CD-1a (17 entity classes),
CD-1b (controllers, services, repositories, gateway, datatypes) and SD-1 (M1 to M35), together with the data
dictionary (M3 section 2.3), the class notes (3.2) and the message table (4.3). The M2 document has no figures; the
M2 slides have none either. The team's own `docs/diagram-conformance.md` listed seven code-side differences as open;
all of them, and six more found on this pass, are now closed in code. The figure-side differences are listed in that
document for the M3 change record.

| # | Design element | Was | Now | Test |
|---|---|---|---|---|
| 9 | SD-1 M30, M31; CD-1b `HandoffResult` | An unavailable mail route was stored as "returned" and used up one of the three resends of FR-084, so an outage of four dispatch cycles silently gave up on the email. | `EmailGateway.send()` returns `HandoffResult.HANDED_OVER` or `UNAVAILABLE`. Unavailable leaves the status "not sent" and the handoff is retried on the next dispatch; only a message the route reports back as *returned* (DF-29, M32 to M35) counts towards the three resends. | `test_unavailable_route_leaves_the_email_not_sent_and_retries_until_the_route_is_back`, gateway tests |
| 10 | DR-011, D9, CD-1b `notify(recipient, type, item)` | Notifications stored only a sentence; the "related item" of DR-011 did not exist, so a notification could not lead anywhere. | `Notification.related_item: ItemRef` (column `related_item`), set by every event (post, connection, conversation, report), returned as `item` in the API; the notifications page opens the item (DF-27). | `test_every_notification_names_the_item_it_is_about`, frontend `linkFor` spec |
| 11 | CD-1b `AuthService.mayAccess(account, item)`; DFD-1 6.2; NFR-013, IF-004 | The access decision was spread across three decorators and several service checks; no single operation answered "may this account reach this item". | `AuthService.may_access()` for pages (`("page","moderation")`, `("page","admin")`), conversations, notifications and reports; `page_required()` and `may_access()` in `security.py` call it; the conversation and notification routes check the item before the service runs. | `test_may_access_refuses_another_students_conversation_notification_and_the_moderator_page` (AC-NFR-013a), `test_may_access_is_one_operation_on_the_auth_service` |
| 12 | DFD-1 DF-23, DF-36, DF-24, 6.6 | DF-23 "moderation decision" includes an escalation choice for upheld reports and 6.4 passes DF-36 to 6.6; the code had no choice, only a separate lookup by report number. | `decide(..., escalate=True)` on an upheld report produces the case summary with the outcome and writes an `ESCALATION` audit entry; refused on a dismissed report. The moderation page shows the choice when the decision is upheld and displays the summary. | `test_upheld_decision_with_the_escalation_choice_returns_the_case_summary`, `test_a_dismissed_report_cannot_be_escalated`, frontend spec |
| 13 | DFD-1 DF-25; 6.4 "recorded as a later note" | The endpoint existed but no page offered it, so a conduct decision from Student Affairs had nowhere to go. | "Later note on a closed report" form on the moderation page. | `test_a_conduct_decision_from_student_affairs_is_recorded_as_a_later_note`, frontend spec |
| 14 | DFD-0 DF-06; process 2.0 owns FR-082 | The email notification choice was reachable only through the notifications endpoint (7.0); the design carries it in the profile details. The notifications page also always showed the switch as on. | `emailNotifications` in `GET`/`PUT /api/profile`; the notifications list returns the stored choice and the page shows it. | `test_email_choice_is_part_of_the_profile` |
| 15 | CD-1b `ConnectionController.respond(session, connectionId, accept)` | Only `/accept` and `/decline` routes. | `POST /api/connections/{id}/respond` with `accept` (the two routes kept). | `test_respond_route_accepts_or_declines_with_one_flag` |
| 16 | CD-1a `AuditRecord {action, itemRef, at}`; D12 | Item and detail were joined into one text column; no entity class. | `AuditRecord` dataclass; column `item_ref` kept apart from `detail`; `AuditLog.entries()` returns records. | `test_audit_record_keeps_action_item_and_detail_apart` |
| 17 | CD-1a `SystemSetting {name, value, changedAt}` | No entity class; the administration page could not show when a limit was last changed. | `SystemSetting` dataclass returned by `SettingsProvider.all()` with `changedAt` and `changedBy`. | `test_settings_are_system_setting_entities_with_their_change_time` |
| 18 | CD-1a `Community.createdAt`; D4 "created time" | Missing. | Column and attribute, set on creation. | `test_community_records_its_creation_time` |
| 19 | CD-1b `EmailMessage {to, subject, body, notificationId}`; DF-29 message reference | No message reference, so a delivery status could not be matched to its notification. | `EmailMessage.notification_id`, set on dispatch and sent as a header by the live gateway. | gateway tests |
| 20 | CD-1b `StubEmailGateway.sentMessages()` | Attribute `sent` only. | `sent_messages()` operation (attribute kept). | gateway tests |
| 21 | M3 section 3.2 enumerations `PostKind`, `CommunityKind`, `ContentStatus`, `ContactRange` | Plain string tuples. | Enumeration types; the validation lists derive from them. | `test_enumerations_match_the_m3_table` |
| 22 | Existing databases | | The three new columns are added by `init_db` to a database created before this pass; data is kept. | `test_schema_migration_adds_the_new_columns_to_an_older_database` |

Not changed, because the difference is in the figure rather than the code: `Account.firstFailedAt` (needed for FR-009,
missing from CD-1a), the DFD-0 "decline wait" arrow drawn into 3.0 instead of 4.0, the missing D1 to 8.0 flow for active
users, and the process that owns the OR-002 clean-up. These are listed in `docs/diagram-conformance.md` for the M3
change record (CH-16 onward).

## 7. After this review (20 November, evening)

Changes made after the review above, so that this file stays accurate:

- FR-026 (student-proposed interest communities, deferred in M2) is now partly built: a student can suggest an interest
  and only the administrator creates the community. Section 3's line "FR-026 absent" is therefore out of date; see
  `docs/deferred-requirements.md`.
- A moderator can open the reported post, its thread and the earlier reports about the student from the queue
  (FR-064); notifications saved before items were stored open the page for their event.
- The interface was redesigned (community names on posts, chat panel, side sections, avatars). Counts are now 180
  backend and 32 frontend tests.
