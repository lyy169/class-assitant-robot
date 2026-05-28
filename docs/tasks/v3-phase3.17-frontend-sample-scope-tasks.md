# V3 Phase 3.17 Tasks: Frontend Sample Scope And Legacy Data Isolation

## Task 1: Audit Existing WIP

- Review current diffs in `cloud_backend/postgres_repository.py`, `cloud_backend/teacher_pages.py`, `cloud_backend/admin_pages.py`, and `cloud_backend/dashboard_v11.py`.
- Keep existing WIP only when it matches the Phase 3.17 spec.
- Remove duplicated, broken, or partially inserted presentation logic by replacing it with a smaller consistent implementation.
- Do not revert unrelated user changes.

Acceptance:

- The four touched Python files compile.
- WIP behavior is traceable to the spec.
- No unrelated frontend redesign or algorithm work is introduced.

## Task 2: Repository Presentation Scope

- Add one backend helper path that classifies result rows into `record_kind` values.
- Add `presentation_scope`, `display_metrics`, `display_badge`, and `record_kind` to frontend-facing item/detail payloads.
- Ensure default teacher report/trend lists exclude historical SAV versions, smoke-test clips, and old legacy test data.
- Ensure default teacher/admin result pages avoid stale legacy records unless they are explicitly labeled.
- Keep raw payload unchanged.

Acceptance:

- Final sample is `competition_final`.
- `phase37_full_classroom_sav_20200908_17` is historical and hidden from default formal reports/trends.
- `phase35_local_imported_sav_full_classroom_20200908_17` is smoke-test/demo and hidden from default formal reports/trends.
- Old `video_video` records are legacy test data and hidden from default formal reports/trends.
- `cls_20260417_101_001` / `video_20260417_001` is treated as legacy visual-only data and hidden from default competition report/trend views unless explicitly labeled.

## Task 3: Dashboard Final Sample Guardrails

- Preserve video display for the final sample.
- Preserve ASR transcript/question/response metrics.
- Preserve activity timeline and event distribution where data exists.
- Hide attention, average attention, student count, all-zero stage distribution, `audio=false`, and zero interaction score from primary display for the final SAV ASR sample.
- Avoid high-risk overclaim when the risk comes from unavailable visual metrics.

Acceptance:

- Dashboard still contains video markup for the final sample.
- Dashboard shows 764 transcript segments, 35 question candidates, and 16 detected responses.
- Dashboard does not show the all-zero attention/stage/student metrics as primary cards.

## Task 4: Teacher Frontend Pages

- Apply the same scope contract to teacher home, classroom records, report center, and trends.
- Default report center should show the final formal sample, not duplicate historical versions.
- Demo/all/history exposure must show clear labels and notes.

Acceptance:

- `/teacher/reports` default includes Phase 3.14 final sample.
- `/teacher/reports` default excludes Phase 3.7, Phase 3.5, and old `video_video` test records.
- `/teacher/trends` default does not compute trend/risk summaries from hidden historical/demo/test records.

## Task 5: Admin Frontend Pages

- Apply scope contract to admin results and admin trends.
- Keep platform observability useful, but label demo/history/test data if exposed.
- Avoid using stale legacy records as default demo headline evidence.

Acceptance:

- `/admin/results` does not present stale legacy `video_video` records as normal classroom evidence by default.
- `/admin/trends` default summaries are based on eligible records.
- Broader views label demo/history/test rows.

## Task 6: Validation Script

- Add `scripts/validate_phase3_17_frontend_sample_scope.sh`.
- Validate health, teacher/admin login, dashboard, teacher report list/detail, teacher trends, admin results, and admin trends.
- Emit all Phase 3.17 markers.

Acceptance:

```text
PHASE317_FRONTEND_SAMPLE_SCOPE_READY=true
```

## Task 7: Status Documentation

- Update `docs/project-status/v3-phase3.17-frontend-sample-scope.md` after implementation and validation.
- Record runtime validation output.
- Clearly state that no database rows were deleted and no metrics were fabricated.
