# Deferred and partly met requirements

What was not built, or was built with a stated limit. Priorities and release status come from M2 section 2.6 (128 baseline requirements, 4 deferred).

## Deferred in M2 (Could priority, not in release 1)

| ID | Requirement | Reason given in M2 |
|---|---|---|
| FR-016 | Major and minor tags on the profile | Not needed to test G-01 to G-03; adds personal data (BR-03). |
| FR-026 | Student created interest communities (proposed by a student, approved by the administrator) | Not needed to test G-01 to G-03. Administrators create interest communities (FR-021, FR-102). |
| FR-049 | Blocking a student | Reporting and removal of connections cover the pilot. |
| NFR-017 | Export of stored data in a documented text form | Not needed for the pilot. |

## Baseline requirements built with a limit

| ID | Status | Detail |
|---|---|---|
| FR-092 | Partly met | Cohort figures are per cohort group. The weekly rows are overall, not split by cohort. |
| FR-005 | Partly met | After verification the student goes to sign-in. The profile form then opens at once, because the profile is required before other features (FR-010). The SRS says the student goes straight to profile creation. |
| IF-003 | Partly met | The live SMTP gateway exists and is chosen with `EMAIL_MODE=live`, but was not tested against the RIT mail server (Q-04, CON-009). |
| OR-001, OR-002 | Partly met | Retention periods are settings (messages 120 days, logs 365 days) and the rule that selects what to keep is tested, but nothing runs it on a schedule. |
| FR-066 and 6.3 to 6.4 | Assumption | A decision can be recorded only after the report has been acknowledged. |
| FR-092 | Assumption | Pilot week 1 starts at the first account creation. An active user is one who signed in within the last 7 days. |

## Baseline requirements not built or not checked

| ID | Status | Detail |
|---|---|---|
| IF-006, NFR-010 | Deployment | HTTPS and TLS depend on where the system is hosted. Nothing in the code forces a redirect. |
| NFR-007, NFR-006 | Not built | No backup, restore or availability monitoring. |
| IF-005, NFR-018, NFR-019, NFR-020 | Not checked | No browser matrix, accessibility audit or usability test was run (M2 OI-06 also records this). |
| NFR-001 to NFR-005 | Not measured | No load or response-time tests were run. |
| OR-004 | Process | Inviting pilot students is a team and Student Affairs procedure, not a software feature. |
| DF-24, DF-25 | Proposed only | Student Affairs flows stay as proposed in M3 (Q-01, Q-05). The case summary (FR-070) is produced on demand and nothing is sent. |

Other choices: withdrawn connections stay in the `connections` table; request timing is kept anonymised after an account is deleted.
