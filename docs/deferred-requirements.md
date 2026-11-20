# Deferred and partly met requirements

What was not built, or was built with a stated limit. Priorities and release status come from M2 section 2.6 (128 baseline requirements, 4 deferred).

## Deferred in M2 (Could priority, not in release 1)

| ID | Requirement | Reason given in M2 |
|---|---|---|
| FR-016 | Major and minor tags on the profile | Not needed to test G-01 to G-03; adds personal data (BR-03). |
| FR-049 | Blocking a student | Reporting and removal of connections cover the pilot. |
| NFR-017 | Export of stored data in a documented text form | Not needed for the pilot. |

## Built beyond the M2 baseline

| ID | Status | Detail |
|---|---|---|
| FR-026 | Partly built | M2 defers student-proposed interest communities. A student can now suggest an interest on the profile page ("Suggest an interest"); nothing is created until the administrator creates the community or dismisses the suggestion, so FR-021 and FR-102 still hold and a student cannot create a community. Each student can have 5 suggestions waiting. This goes beyond the M2 baseline and should be recorded as a change (next M3 revision). |

## Baseline requirements built with a limit

| ID | Status | Detail |
|---|---|---|
| FR-092 | Partly met | Cohort figures are per cohort group. The weekly rows are overall, not split by cohort. |
| FR-005 | Partly met | After verification the student goes to sign-in. The profile form then opens at once, because the profile is required before other features (FR-010). The SRS says the student goes straight to profile creation. |
| IF-003 | Partly met | The live SMTP gateway exists and is chosen with `EMAIL_MODE=live`, but was not tested against the RIT mail server (Q-04, CON-009). |
| OR-001, OR-002 | Partly met | Retention periods are settings (messages 120 days, logs 365 days). The clean-up runs from the administration endpoint or `flask --app app clean-up` and is tested; the daily schedule is a job on the host and is not in the code. |
| FR-066 and 6.3 to 6.4 | Assumption | A decision can be recorded only after the report has been acknowledged. |
| FR-092 | Assumption | Pilot week 1 starts at the first account creation. An active user is one who signed in within the last 7 days. |

## Baseline requirements not built or not checked

| ID | Status | Detail |
|---|---|---|
| IF-006, NFR-010 | Partly met | `FORCE_HTTPS=1` redirects plain HTTP, sends HSTS, marks the session cookie secure and refuses a placeholder secret key; the email leg needs TLS 1.2. It is off by default and needs a host with a certificate. |
| NFR-007, NFR-006 | Not built | No backup, restore or availability monitoring. |
| IF-005, NFR-018, NFR-019, NFR-020 | Partly checked | Form fields are labelled and messages are announced to screen readers (NFR-019), and the layout was checked in desktop Chrome at 1100 px and 375 px. No browser matrix, automated accessibility check or usability test was run (M2 OI-06 also records this). |
| NFR-001, NFR-003 | Not measured | No load test was run. NFR-002 holds by design and NFR-005 was timed by hand (see `requirements-coverage.md`). |
| OR-004 | Process | Inviting pilot students is a team and Student Affairs procedure, not a software feature. |
| DF-24, DF-25 | Proposed only | Student Affairs flows stay as proposed in M3 (Q-01, Q-05). The case summary (FR-070) is produced on demand and nothing is sent. |

Other choices: withdrawn connections stay in the `connections` table; request timing is kept anonymised after an account is deleted.
