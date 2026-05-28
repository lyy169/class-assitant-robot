# V3 Phase 3.19 Status: Remove Trend Insights From Frontend

## Goal

Remove the Trend Insights frontend surface because the current cloud demo has one final ASR-enhanced full-classroom sample and cannot honestly support multi-lesson trend conclusions.

## Scope

- Removed visible teacher/admin navigation links to trend pages.
- Removed trend entry buttons from teacher home and dashboard.
- Redirected `/teacher/trends` to `/teacher/reports`.
- Redirected `/admin/trends` to `/admin/results`.
- Kept `/api/teacher/trends` and `/api/admin/trends` for backward compatibility and historical validation scripts.

## Non-Goals

- No database deletion.
- No demo or historical data deletion.
- No video re-upload.
- No local analyzer or Raspberry Pi code changes.
- No upload API changes.
- No git commit in this phase.

## Validation

Static validation:

```bash
python -B -m py_compile cloud_backend/main.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/dashboard_v11.py
bash -n scripts/validate_phase3_19_remove_trend_insights.sh
```

Runtime validation after manually restarting the service:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_19_remove_trend_insights.sh
```

Expected result:

- `PHASE319_FRONTEND_TRENDS_REMOVED=true`
- Teacher/admin trend page routes redirect to report/data pages.
- Dashboard, teacher home, and admin home no longer link to trend pages.
