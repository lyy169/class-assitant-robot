# V3 Phase 3.18 Tasks: Demo Trend Visualization Scope

## Task 1: Audit Current Trend Demo Support

- Review `/teacher/trends` and `/admin/trends` pages.
- Review `get_phase3_teacher_trends` and `get_phase3_admin_trends`.
- Review `scripts/seed_phase3_demo_trend_data.sh`.
- Confirm whether demo trend records already exist.

Acceptance:

- Existing demo filter behavior is understood before edits.
- No Phase 3.17 real-data filtering is loosened.

## Task 2: Ensure Demo Trend Data Exists

- Use existing `scripts/seed_phase3_demo_trend_data.sh --seed` only if demo trend data is missing or insufficient.
- Keep demo records labeled as `dataset.source=demo` and `dataset.purpose=phase3_trend_seed`.
- Do not delete or alter real classroom records.

Acceptance:

- At least 5 demo trend lessons are available for trend visualization.
- Seeded demo data is clearly marked as demo.

## Task 3: Teacher Trend Demo Display

- Make `data_source=demo` easy to select or link from the page.
- Show a visible demo warning when demo/all data is active.
- Keep trend charts visible for demo data: feedback, attention/activity, question/response, stage structure.
- Show priority review/risk list and rule recommendations when data supports it.

Acceptance:

- `/teacher/trends?data_source=demo&limit=20` is reachable.
- API returns demo-scoped series with multiple labels.
- Demo warning is visible in HTML or rendered page.

## Task 4: Admin Trend Demo Display

- Ensure `/admin/trends?data_source=demo&limit=30` works.
- Label demo trend data clearly.
- Keep overview, rankings, teacher activity, risk lessons, and recent reports coherent.

Acceptance:

- Admin demo trend API returns demo-scoped payload.
- Demo warning or quality note is present.

## Task 5: Preserve Real/Demo Separation

- Real trend pages stay real by default.
- Report center default does not become a demo data list.
- Phase 3.14 remains the real final dashboard sample.
- Demo trend data is never presented as true classroom evidence.

Acceptance:

- `data_source=real` trend payloads do not include demo records.
- Default reports do not include `demo_phase3_*` records.
- Final dashboard sample remains reachable and unchanged.

## Task 6: Validation And Status

- Add `scripts/validate_phase3_18_demo_trend_visualization_scope.sh`.
- Run static checks and runtime validation.
- Update `docs/project-status/v3-phase3.18-demo-trend-visualization-scope.md` with markers.

Final marker:

```text
PHASE318_DEMO_TREND_VISUALIZATION_READY=true
```
