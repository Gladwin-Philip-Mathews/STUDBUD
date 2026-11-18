# Deferred and partly met requirements

What was not built, or was built with a stated limit. This is the honest gap list for the 20 November submission.

| ID | Status | Detail |
|---|---|---|
| FR-016 | Deferred | Deferred in M3. Not built. |
| FR-026 | Deferred | Deferred in M3. Not built. |
| FR-049 | Deferred | Deferred in M3. Not built. |
| DF-24, DF-25 | Proposed only | Student Affairs hand-over flows stay as proposed in M3. No code. |
| IF-003 | Partly met | The live SMTP gateway exists and is chosen with `EMAIL_MODE=live`, but was not tested against the real RIT mail server. |
| OR-002 | Partly met | Retention periods are settings (messages 120 days, logs 365 days). The rule that selects what to keep is built and tested, but nothing runs it on a schedule. |
| Pilot report | Assumption | Pilot week 1 starts at the first account creation. "Active user" means signed in within the last 7 days. |
| Pilot report | Limit | Weekly figures are overall, not per cohort group. Group figures are per cohort. |
| Moderation 6.3 to 6.4 | Assumption | A decision can be recorded only after the report has been acknowledged. |
| Performance | Not measured | No load or response-time tests were run. |

Other assumptions: withdrawn connections stay in the `connections` table; request timing is kept anonymised after an account is deleted.
