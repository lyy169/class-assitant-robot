# V3 Phase 3.18 Demo Trend Visualization Scope Status

## Status

Phase 3.18 validation passed. Demo trend data was already present, so no seeding was performed in this closeout run.

## Goal

Use clearly labeled demo trend data to demonstrate multi-lesson trend visualization and trend analysis ability, without weakening Phase 3.17 real-data separation.

## Final Real Sample Remains

```text
phase314_asr_full_classroom_sav_20200908_17
```

This remains the real full-classroom ASR dashboard sample.

## Demo Trend Scope

Demo trend data may use:

```text
demo_phase3_001 ... demo_phase3_008
```

These records are for visualizing what the platform looks like after multiple lessons accumulate. They must be labeled as demo data and must not be treated as real classroom evidence.

## Desired Demo Trend Capabilities

Teacher trend page should demonstrate:

- Teaching feedback trend line.
- Attention/activity trend.
- Question/response trend.
- Teaching stage structure.
- Review priority/risk list.
- Rule recommendations.

Admin trend page should demonstrate:

- Platform overview metrics.
- Classroom ranking.
- Teacher activity.
- Risk lessons.
- Recent reports.

## Current Implementation Notes

Existing code already contains:

```text
/teacher/trends data_source=real/demo/all
/admin/trends data_source=real/demo/all
scripts/seed_phase3_demo_trend_data.sh
```

The current teacher/admin trend pages already expose `data_source=demo` and show demo scope warnings. Phase 3.18 validation confirms this behavior is sufficient without loosening Phase 3.17 real-data filters.

## Runtime Spot Check

Browser/API spot check on `2026-05-10` found demo trend data already present, so seeding was not needed during SDD preparation:

```text
/teacher/trends?data_source=demo&limit=20 reachable=true
demo warning visible=true
teacher demo lesson_count=10
teacher demo series label_count=10
teacher demo recommendations=6
teacher demo charts present=true
/admin/trends?data_source=demo&limit=30 api_ok=true
admin demo lesson_count=10
admin classroom_rankings=1
admin teacher_activity=1
admin recent_reports=10
real trend contains demo_phase3=false
real reports contain demo_phase3=false
```

The validation script was run against the active cloud service on port `8011`; all Phase 3.18 markers passed.

## 3.18b Entry Visibility Fix

After user feedback, the default `/teacher/trends` page was rechecked and the issue was reproduced: the page defaulted to `data_source=real`, real trend data was empty, and demo data existed only behind the dropdown. That made the page look like there was no demo trend visualization.

Prepared a small frontend-only fix:

- Add a visible `查看演示趋势数据` entry on `/teacher/trends`.
- Add a visible `查看平台演示趋势` entry on `/admin/trends`.
- Add clickable demo CTA inside the real-data-insufficient warning.
- Update Phase 3.18 validation script to require these default-page demo entries.

Static compile passed for:

```text
cloud_backend/teacher_pages.py
cloud_backend/admin_pages.py
```

Runtime page still needs the running `8011` process to reload these template changes before final browser validation.

## Validation Plan

Use:

```bash
scripts/validate_phase3_18_demo_trend_visualization_scope.sh
```

Expected final marker:

```text
PHASE318_DEMO_TREND_VISUALIZATION_READY=true
```

## Checklist

- [x] Audit current demo trend behavior.
- [x] Confirm demo trend data exists.
- [x] Demo data seeding not needed.
- [x] Ensure teacher demo trend page has clear demo warning.
- [x] Ensure admin demo trend page has clear demo warning/scope note.
- [x] Ensure real trend scope remains real.
- [x] Ensure default reports remain non-demo.
- [x] Run static validation.
- [x] Run runtime validation.
- [x] Paste markers here.

## Validation Results

Static validation:

```text
python no-write compile check: passed
bash -n scripts/validate_phase3_18_demo_trend_visualization_scope.sh: passed
```

Runtime validation:

```text
PHASE318_DEMO_TREND_SEED_SCRIPT_PRESENT=true
PHASE318_TEACHER_LOGIN_OK=true
PHASE318_ADMIN_LOGIN_OK=true
PHASE318_TEACHER_TRENDS_DEMO_PAGE_REACHABLE=true
PHASE318_TEACHER_TRENDS_DEMO_WARNING_VISIBLE=true
PHASE318_TEACHER_TRENDS_DEMO_API_OK=true
PHASE318_TEACHER_TRENDS_DEMO_DATA_AVAILABLE=true
PHASE318_TEACHER_TRENDS_DEMO_SERIES_OK=true
PHASE318_TEACHER_TRENDS_DEMO_CHARTS_PRESENT=true
PHASE318_TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT=true
PHASE318_ADMIN_TRENDS_DEMO_PAGE_REACHABLE=true
PHASE318_ADMIN_TRENDS_DEMO_API_OK=true
PHASE318_ADMIN_TRENDS_DEMO_SCOPE_OK=true
PHASE318_REAL_TRENDS_SCOPE_STILL_REAL=true
PHASE318_REPORTS_DEFAULT_NOT_DEMO=true
PHASE318_PHASE314_FINAL_SAMPLE_UNCHANGED=true
PHASE318_NO_DEMO_AS_REAL_CLAIM=true
PHASE318_DEMO_TREND_VISUALIZATION_READY=true
```

## Boundaries

- No DB deletion.
- No demo-as-real claim.
- No fake real metrics.
- No final video re-upload.
- No core algorithm changes.
- No local analyzer or Raspberry Pi changes.
- No git commit.
