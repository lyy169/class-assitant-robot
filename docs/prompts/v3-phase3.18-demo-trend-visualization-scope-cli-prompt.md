# V3 Phase 3.18 CLI Prompt Summary

Work in `/root/video_project_src`.

Follow:

```text
docs/specs/v3-phase3.18-demo-trend-visualization-scope-spec.md
docs/tasks/v3-phase3.18-demo-trend-visualization-scope-tasks.md
docs/runbooks/v3-phase3.18-demo-trend-visualization-scope-runbook.md
```

## Goal

Make trend insight pages demo-ready by showing clearly labeled demo trend data when `data_source=demo` is selected, while keeping Phase 3.17 real-data separation intact.

## Required Behavior

- `/teacher/trends` defaults to real data.
- `/teacher/trends?data_source=demo&limit=20` shows demo trend visualization ability.
- `/admin/trends?data_source=demo&limit=30` shows labeled demo platform trend ability.
- Demo view clearly states that demo trend data is for competition/function demonstration and not a real classroom conclusion.
- Use existing `scripts/seed_phase3_demo_trend_data.sh --seed` only if demo trend data is missing or insufficient.
- Do not put demo data into default real report center.
- Do not loosen Phase 3.17 filters for historical/test records.
- Keep `phase314_asr_full_classroom_sav_20200908_17` as the final real dashboard sample.

## Suggested UI/Copy

Use clear wording similar to:

```text
当前为演示趋势数据，用于展示系统在多堂课累计后的趋势分析与可视化能力，不作为真实课堂采集结论。
```

## Do Not

- Claim demo data is real.
- Delete DB data.
- Rewrite final sample payload.
- Re-upload videos.
- Modify core visual/ASR algorithms.
- Modify local analyzer or Raspberry Pi code.
- Commit git changes.

## Validation

Add or update:

```text
scripts/validate_phase3_18_demo_trend_visualization_scope.sh
docs/project-status/v3-phase3.18-demo-trend-visualization-scope.md
```

Run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/auth.py
bash -n scripts/validate_phase3_18_demo_trend_visualization_scope.sh
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_18_demo_trend_visualization_scope.sh
```

Final marker:

```text
PHASE318_DEMO_TREND_VISUALIZATION_READY=true
```

Update the status doc with exact markers and note whether demo data was seeded or already present.
