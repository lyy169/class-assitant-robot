# V3 Phase 3.19 Runbook: Remove Trend Insights From Frontend

## Why

Trend insight pages require multiple comparable real classroom sessions. The current competition-ready sample set centers on:

```text
phase314_asr_full_classroom_sav_20200908_17
```

Without more real sessions, frontend trend charts can mislead users. The safer product choice is to remove Trend Insights from the visible frontend and focus the demo on dashboard evidence, classroom reports, and admin data/status pages.

## What Changed

- `/teacher` no longer links to Trend Insights.
- `/dashboard` no longer links to Trend Insights.
- `/admin` no longer links to Trend Insights.
- `/teacher/trends` redirects to `/teacher/reports`.
- `/admin/trends` redirects to `/admin/results`.
- Existing trend APIs remain available for compatibility.

## Static Check

```bash
cd /root/video_project_src
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/main.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/dashboard_v11.py
bash -n scripts/validate_phase3_19_remove_trend_insights.sh
```

## Runtime Check

After the cloud backend is manually restarted:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_19_remove_trend_insights.sh
```

Expected final marker:

```text
PHASE319_FRONTEND_TRENDS_REMOVED=true
```

## Notes

This phase does not delete data, remove trend API compatibility, modify upload interfaces, or change the final ASR classroom sample.
