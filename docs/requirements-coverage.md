# Requirements coverage

Generated from the requirement IDs cited in code comments and test names, then checked by hand. **Tests** lists tests that cite the ID. Where none does, the **Note** says how it is covered or that it is not.


## Functional (FR)

| ID | Code | Tests | Note |
|---|---|---|---|
| FR-001 | `services/auth_service.py` | `test_register_creates_unverified_account_and_sends_one_message`, `test_unverified_account_cannot_sign_in` |  |
| FR-002 | not cited in code | `test_non_rit_domains_rejected_no_account_no_message` |  |
| FR-003 | not cited in code | `test_display_name_rules`, `test_password_rules_name_the_field` |  |
| FR-004 | `controllers/auth.py`, `services/auth_service.py` | `test_duplicate_email_gives_same_message_and_no_second_account` |  |
| FR-005 | `services/auth_service.py` | `test_expired_link_leaves_account_unverified`, `test_token_validity`, `test_verify_within_24_hours_then_link_is_single_use` |  |
| FR-006 | `services/auth_service.py` | `test_expired_link_leaves_account_unverified`, `test_resend_limit_three_per_hour_and_old_links_stop_working`, `test_token_validity` |  |
| FR-007 | `services/auth_service.py` | `test_unverified_account_cannot_sign_in` |  |
| FR-008 | `models/entities.py`, `services/auth_service.py` | `test_sign_in_success_and_me`, `test_unverified_or_suspended_cannot_sign_in`, `test_wrong_password_and_unknown_email_same_message` |  |
| FR-009 | `models/entities.py`, `services/auth_service.py` | `test_lockout_after_five_failures_then_released`, `test_unverified_or_suspended_cannot_sign_in` |  |
| FR-010 | `auth/auth.guard.ts`, `auth/auth.service.ts` (+2) | `marks the profile complete after a successful save (FR-010)`, `returns the named field errors when the backend refuses (AC-FR-010a)`, `test_features_are_closed_until_the_profile_exists` (+1) |  |
| FR-011 | `repositories/interfaces.py`, `services/profile_service.py` | `test_only_courses_on_the_active_list_can_be_added` |  |
| FR-012 | `services/profile_service.py` | `test_interest_limits` |  |
| FR-013 | not cited in code | `test_edits_show_up_in_suggestions` |  |
| FR-014 | `models/enums.py`, `services/profile_service.py` | `test_others_see_only_four_items` |  |
| FR-015 | `repositories/interfaces.py`, `services/community_service.py` (+1) | `test_deleted_student_shows_as_deleted_student`, `test_deleting_the_account_removes_its_messages`, `test_deleting_the_account_removes_the_personal_data` |  |
| FR-020 | `services/admin_service.py`, `services/community_service.py` (+1) | `test_adding_a_course_makes_its_community_and_rejects_duplicates` |  |
| FR-021 | `services/community_service.py` | `test_only_administrators_create_interest_communities` |  |
| FR-022 | `services/profile_service.py` | `test_adding_a_course_puts_the_student_in_its_community`, `test_removing_the_course_takes_the_student_out` |  |
| FR-023 | `services/community_service.py` | `test_joining_rules` |  |
| FR-024 | `services/community_service.py` | `test_search_communities_by_part_of_the_name` |  |
| FR-025 | `services/admin_service.py`, `services/community_service.py` | `test_archived_community_stays_readable_but_refuses_new_content`, `test_archived_course_cannot_be_added_but_existing_students_keep_it` |  |
| FR-030 | `services/community_service.py` | `test_post_limits_and_named_problems` |  |
| FR-031 | `communities/community-page.ts` | `returns each named problem when a post is refused (FR-031)`, `test_post_limits_and_named_problems` |  |
| FR-032 | `services/community_service.py` | `test_reply_notifies_the_author_in_time_order` |  |
| FR-033 | `models/content.py`, `repositories/community_repo.py` (+2) | `test_author_can_delete_others_cannot`, `test_deleted_post_stays_visible_to_the_moderator`, `test_edit_within_15_minutes_then_not` |  |
| FR-034 | `repositories/community_repo.py`, `services/community_service.py` | `test_feed_is_newest_first_with_20_per_page_and_kind_filter` |  |
| FR-035 | `repositories/community_repo.py`, `services/community_service.py` | none cited | Post page with replies; covered by community tests (not cited by ID). |
| FR-036 | `services/community_service.py` | `reports a too-short search without throwing (FR-036)`, `test_search_posts` |  |
| FR-037 | `services/community_service.py` | `asks the feed for one kind at a time (FR-037)`, `test_feed_is_newest_first_with_20_per_page_and_kind_filter` |  |
| FR-038 | `communities/post-page.ts` | none cited | Connect button on posts; frontend only, checked by hand. |
| FR-039 | `moderation/report-form.ts` | `test_adding_a_course_puts_the_student_in_its_community` |  |
| FR-040 | `models/entities.py`, `services/connection_service.py` | `test_email_is_handed_over_after_response_in_production_mode` |  |
| FR-041 | `services/connection_service.py` | `test_email_is_handed_over_after_response_in_production_mode` |  |
| FR-042 | not cited in code | `test_note_over_200_characters_is_rejected`, `test_request_is_pending_and_receiver_is_notified` |  |
| FR-043 | `communities/post-page.ts`, `controllers/connections.py` (+1) | `test_recent_decline_blocks_for_30_days_without_saying_declined` |  |
| FR-044 | `services/connection_service.py` | `test_accept_lists_both_and_notifies_requester` |  |
| FR-045 | `services/connection_service.py` | `test_decline_tells_requester_only_not_accepted` |  |
| FR-046 | `services/connection_service.py` | `test_withdraw_removes_request_for_receiver` |  |
| FR-047 | `services/connection_service.py` | none cited | Connection list; covered by connection API tests. |
| FR-048 | `services/connection_service.py` | `test_remove_ends_connection_for_both` |  |
| FR-050 | `services/messaging_service.py` | `test_length_limits`, `test_message_is_delivered_and_the_receiver_is_notified` |  |
| FR-051 | `services/messaging_service.py` | `shows the plain refusal when the connection is not accepted (FR-051)`, `test_refused_unless_connection_is_accepted_and_nothing_is_stored` |  |
| FR-052 | `messaging/messaging-home.ts`, `services/messaging_service.py` | `test_conversations_most_recent_first_with_unread_count`, `test_messages_are_in_time_order` |  |
| FR-053 | `moderation/report-form.ts`, `services/moderation_service.py` | `test_can_report_a_student_a_reply_and_a_message` |  |
| FR-054 | `services/moderation_service.py` | `test_moderator_sees_message_text_only_through_a_report_and_each_access_is_logged` |  |
| FR-060 | `moderation/moderation.service.ts`, `moderation/report-form.ts` (+1) | `sends the item type, id and reason of a report (FR-060)`, `test_can_report_a_student_a_reply_and_a_message`, `test_report_records_reporter_item_reason_and_appears_in_the_queue` (+1) |  |
| FR-061 | `services/moderation_service.py` | `test_report_records_reporter_item_reason_and_appears_in_the_queue` |  |
| FR-062 | `models/moderation.py`, `services/moderation_service.py` | `test_queue_is_oldest_first_and_flags_overdue` |  |
| FR-063 | `models/moderation.py`, `services/moderation_service.py` | `test_acknowledgement_notifies_and_keeps_the_report_open` |  |
| FR-064 | `services/moderation_service.py` | `returns the named problem when a decision is incomplete (FR-064)`, `test_decision_needs_decision_action_and_note` |  |
| FR-065 | `controllers/communities.py`, `models/content.py` (+3) | `test_hidden_content_is_removed_from_others_but_author_sees_a_notice`, `test_hidden_message_is_removed_for_the_receiver`, `test_hidden_message_shows_only_to_its_sender` (+1) |  |
| FR-066 | `services/auth_service.py`, `services/moderation_service.py` | `test_suspended_account_loses_access_at_next_request`, `test_suspension_ends_the_session_refuses_sign_in_and_hides_from_suggestions` |  |
| FR-067 | `services/moderation_service.py` | `test_closed_decision_cannot_change_but_a_dated_note_can_be_added` |  |
| FR-068 | `services/moderation_service.py` | `test_closing_tells_the_reporter_without_the_action_or_name` |  |
| FR-069 | `services/moderation_service.py` | `test_cannot_report_yourself_but_two_reports_on_one_item_are_kept`, `test_report_text_limit_and_reason_required` |  |
| FR-070 | `services/moderation_service.py` | `test_case_summary_only_for_upheld_and_has_no_other_messages` |  |
| FR-080 | `app.ts`, `notifications/notifications.service.ts` (+2) | `test_reply_notifies_the_author_in_time_order`, `test_requests_need_sign_in` |  |
| FR-081 | `email_gateway/gateway.py`, `services/messaging_service.py` (+1) | `test_email_names_the_sender_and_is_sent_after_the_request`, `test_message_is_delivered_and_the_receiver_is_notified`, `test_no_email_when_switched_off_but_in_app_stays` |  |
| FR-082 | `services/notification_service.py` | `test_no_email_when_switched_off_but_in_app_stays` |  |
| FR-083 | `services/notification_service.py` | `test_notification_list_newest_first_read_and_read_all` |  |
| FR-084 | `services/notification_service.py` | `test_requests_need_sign_in`, `test_resend_limit_is_three`, `test_returned_status_triggers_resend_up_to_three_times` (+1) |  |
| FR-090 | `controllers/onboarding.py`, `profiles/onboarding-question.ts` (+1) | `sends `, `test_question_is_asked_again_in_week_12_and_both_answers_are_stored`, `test_question_is_asked_once_and_skipping_is_recorded` |  |
| FR-091 | `repositories/interfaces.py`, `services/connection_service.py` (+1) | `test_connection_keeps_row_after_account_deleted`, `test_request_timing_is_kept_without_identity_after_deletion` |  |
| FR-092 | `services/pilot_service.py` | `test_change_between_week_1_and_week_12`, `test_report_figures_match_the_hand_calculation`, `test_request_timing_is_kept_without_identity_after_deletion` |  |
| FR-093 | `services/pilot_service.py` | `test_a_group_under_five_is_combined_not_shown_alone`, `test_merge_rules` |  |
| FR-094 | `models/pilot.py`, `services/pilot_service.py` | `test_export_has_no_names_or_email_addresses` |  |
| FR-100 | `services/admin_service.py`, `services/profile_service.py` | `shows the duplicate code message when a course is refused (FR-100)`, `test_adding_a_course_makes_its_community_and_rejects_duplicates`, `test_archived_course_cannot_be_added_but_existing_students_keep_it` (+2) |  |
| FR-101 | `services/admin_service.py` | `test_domain_check_uses_accepted_domains`, `test_removing_a_domain_takes_effect_without_a_restart` |  |
| FR-102 | `services/admin_service.py` | `test_assigning_and_removing_the_moderator_role_is_audited`, `test_interest_communities_can_be_created_renamed_and_archived` |  |
| FR-103 | `repositories/admin_repo.py`, `services/admin_service.py` | `test_system_status_counts_match_the_data` |  |
| FR-104 | `services/admin_service.py`, `settings.py` | `saves a setting by name (FR-104)`, `test_changing_a_setting_applies_on_the_next_view` |  |

## Non-functional (NFR)

| ID | Code | Tests | Note |
|---|---|---|---|
| NFR-004 | `email_dispatch.py`, `services/notification_service.py` | none cited | Email hand-over after the response; checked in notification tests, timing not measured. |
| NFR-009 | `services/auth_service.py` | `test_no_password_or_token_stored_in_clear` |  |
| NFR-011 | `services/auth_service.py` | `test_idle_session_ends_after_two_hours`, `test_recent_decline_blocks_for_30_days_without_saying_declined` |  |
| NFR-012 | `models/entities.py`, `models/moderation.py` (+2) | `test_changed_setting_applies_without_release`, `test_lockout_after_five_failures_in_window`, `test_token_store_and_resend_window` |  |
| NFR-013 | `auth/auth.service.ts`, `security.py` (+1) | `test_only_administrators_reach_admin_endpoints`, `test_only_moderators_reach_the_queue`, `test_pilot_report_is_for_administrators_only` |  |
| NFR-015 | `services/admin_service.py`, `services/audit_log.py` (+1) | `test_decision_is_written_to_the_audit_record` |  |
| NFR-024 | `services/pilot_service.py` | `test_report_states_its_period_and_the_records_used` | Report holds numbers only; checked in pilot tests. |

## Data (DR)

| ID | Code | Tests | Note |
|---|---|---|---|
| DR-001 | not cited in code | `test_email_and_display_name_unique` |  |
| DR-002 | `models/entities.py`, `models/enums.py` (+2) | none cited | Enforced by profile validation (tested under FR-010 to FR-012). |
| DR-003 | `models/enums.py`, `services/profile_service.py` | none cited | Enforced by profile and course archive tests. |
| DR-004 | `services/community_service.py` | none cited | Post kinds checked in community tests (invalid kind refused). |
| DR-008 | `models/content.py`, `services/messaging_service.py` (+1) | none cited | Messages deleted with their connection; covered by messaging tests. |
| DR-009 | `models/enums.py` | none cited | Report reasons and status enums; covered by moderation tests. |
| DR-010 | `models/enums.py` | none cited | Outcome records are append-only in the schema; covered by moderation tests. |
| DR-012 | `models/pilot.py`, `services/pilot_service.py` | none cited | Answer values checked in pilot tests. |
| DR-013 | `db.py`, `repositories/admin_repo.py` (+1) | `test_removing_a_domain_takes_effect_without_a_restart` |  |
| DR-014 | `services/admin_service.py`, `settings.py` | `test_settings_reject_unknown_names_and_bad_values`, `test_unknown_setting_cannot_be_stored` |  |
| DR-015 | `services/audit_log.py` | none cited | Audit entries checked in admin and moderation tests. |

## Interfaces (IF)

| ID | Code | Tests | Note |
|---|---|---|---|
| IF-003 | `email_gateway/gateway.py` | none cited | Live SMTP route; stub tested, live route not tested (needs RIT mail server). |
| IF-004 | not cited in code | `test_only_moderators_reach_the_queue` | Role check tested; the pages are in the admin and moderation areas. |

## Constraints (CON)

| ID | Code | Tests | Note |
|---|---|---|---|
| CON-005 | `services/moderation_service.py` | none cited | Enforced in moderation service; exercised by the moderation tests but not cited by ID. |
| CON-009 | `__init__.py`, `email_gateway/gateway.py` | `test_gateway_is_chosen_by_setting` |  |

## Other (OR)

| ID | Code | Tests | Note |
|---|---|---|---|
| OR-001 | `repositories/message_repo.py`, `repositories/report_repo.py` (+3) | `test_retention_deletes_old_messages_but_keeps_protected_ones`, `test_retention_keeps_messages_named_in_open_reports` |  |
| OR-002 | `settings.py` | none cited | Log retention setting; value tested, scheduled clean-up not built. |
| OR-003 | `db.py`, `models/entities.py` (+1) | `test_registration_needs_the_notice_accepted_and_records_when` |  |


## Added by the implementation review of 20 November 2026

These IDs were not in the tables above. See `docs/REVIEW.md` for the finding behind each row.

| ID | Code | Tests | Note |
|---|---|---|---|
| IF-006 | `__init__.py` (FORCE_HTTPS redirect, HSTS, Secure cookie) | `test_plain_http_is_redirected_and_returns_no_content_when_https_is_enforced`, `test_https_mode_refuses_a_placeholder_secret_key` | Off on a laptop, on with `FORCE_HTTPS=1` on the pilot server. |
| NFR-010 | `email_gateway/gateway.py` (`tls_context`) | `test_email_route_requires_tls_1_2_or_later` | Browser leg is IF-006; the certificate itself is a hosting matter (Q-04). |
| NFR-008 | `__init__.py` (error handlers), `services/community_service.py` (repeat window) | `test_failures_show_a_plain_message_without_technical_details`, `test_a_repeated_post_submission_creates_one_post` | |
| DR-007 | `schema/00_core.sql` (`one_open_connection_per_pair`) | `test_two_open_connections_for_one_pair_cannot_be_stored` | Was enforced in the service only. |
| DR-009 | `schema/40_moderation.sql` (`reports_reason_check`) | `test_a_report_reason_outside_the_list_cannot_be_stored` | |
| DR-011 | `schema/00_core.sql` (`notifications_event_type_check`) | `test_a_notification_with_an_unknown_event_type_cannot_be_stored` | |
| OR-001 | `services/retention_service.py`, `controllers/admin.py`, CLI `clean-up` | `test_clean_up_applies_message_retention_through_the_same_run` | The rule existed but nothing ran it. |
| OR-002 | `services/retention_service.py`, `repositories/report_repo.py`, `services/audit_log.py` | `test_clean_up_deletes_conduct_records_older_than_the_retention_setting`, `test_clean_up_never_deletes_an_open_report` | Append-only triggers stand down only inside the clean-up transaction (FR-067 kept for every role). |
| NFR-019 | Angular templates (aria-label on every unlabeled control, role="alert" / "status" on messages) | none (checked by hand) | Automated checker and screen-reader run still to do (AC-NFR-019a). |
| CON-002 | `__init__.py` (Referrer-Policy), `frontend/src/index.html` | none (inspection) | No third-party script, font or tracker is loaded. |
| DR-011 (related item) | `models/entities.py` `Notification.related_item`, `ItemRef` | `test_every_notification_names_the_item_it_is_about` | Added on the diagram alignment pass; the event type rule is the trigger above. |
| NFR-013 (one access check) | `services/auth_service.py` `may_access`, `security.py` `page_required` | `test_may_access_refuses_another_students_conversation_notification_and_the_moderator_page` | AC-NFR-013a as written: conversation of B and C, notification of B, moderator page. |
| FR-082 (via 2.0) | `controllers/profile.py` | `test_email_choice_is_part_of_the_profile` | DF-06. |
| FR-070 (escalation) | `services/moderation_service.py` `decide(escalate=True)` | `test_upheld_decision_with_the_escalation_choice_returns_the_case_summary` | DF-23, DF-36, DF-24. |


## Constraints, interfaces and qualities that no code comment names

These requirements shape the product rather than one function. Each is checked here against the built system (21 November 2026).

| ID | Status | How it is met or what is left |
|---|---|---|
| CON-001 | Met | Angular web application served over HTTP; no native client and nothing to install on the student's device. |
| CON-003 | Met | Registration accepts only the domains in the accepted-domains list (FR-101); no other university or RIT campus. |
| CON-004 | Met | The RIT email with a single-use link is the only proof of membership (FR-001 to FR-005); no other identity provider. |
| CON-006 | Process | Publicity waits for Student Affairs and Marketing; the pilot runs as an invited, closed test. Nothing in the code publishes or advertises the product. |
| CON-007 | Met | Every post, reply and message shows the verified author's display name (`author` in the post, reply and message JSON); there is no anonymous mode. |
| CON-008 | Process | Semester and team limit; the scope in `docs/deferred-requirements.md` was kept inside it. |
| IF-001 | Met | Pages for registration, sign in, profile, feed, communities, post, connections, conversations, notifications and report, with a navigation bar on every page after sign in; the bar scrolls sideways on a phone and the pages stack at 360 px. The settings page is the notification switch and the profile. |
| IF-002 | Met | Field errors sit next to the field (`role="alert"`), every change confirms with a notice, and server failures return a plain message (TC-NFR-008a). |
| IF-005, NFR-018 | Not yet run | The nine browser and device combinations still need the acceptance script. Layout was checked in desktop Chrome at 1100 px and at 375 px. |
| DR-005, DR-006 | Met | Post and reply fields and limits (`services/community_service.py`, `schema/20_communities.sql`); test `test_post_limits_and_named_problems`. |
| NFR-001, NFR-003 | Not yet run | Needs the 100-student load test and the capacity message. |
| NFR-002 | Met by design | Posts, replies and messages are written to the database before the response and read from it on the next request, so they appear at once; suggestions are computed from the stored profile on each request, so a profile change shows on the next page load. |
| NFR-005 | Met | A search over 10,000 posts took about 10 ms on a laptop (limit 2 s). |
| NFR-006, NFR-007 | Not yet run | Depend on the host: uptime log and a daily backup with one rehearsed restore. |
| NFR-014 | Met | Only the data of DR-001 to DR-015 is stored; retention is applied by the clean-up run (OR-001, OR-002). The interest suggestion stores a community name, the suggesting student and the time, and is removed from the open list when answered. |
| NFR-016 | Met | Every Must requirement has an automated test (see the tables above); settings and courses change from the administration page without code changes (NFR-012, FR-100); the team reviews each pull request before merging (CONTRIBUTING.md). |
| NFR-017 | Deferred | See `docs/deferred-requirements.md`. |
| NFR-020 | Not yet run | Needs the usability test with five students. |
| NFR-021 | Met | English text only, no technical terms on student pages, and each error names the next step. |
| NFR-022 | Met | First load is about 96 kB transferred (350 kB raw), far under 1.5 MB; no third-party fonts, scripts or images. |
| NFR-023 | Met | Nothing requires a connection request or message; a student can leave (FR-015) and switch email off (FR-082). |
| OR-004 | Process | The invited-student list is kept by the team before the first registration. |
| FR-016, FR-026, FR-049 | Deferred | See `docs/deferred-requirements.md`. |
