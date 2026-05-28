# V3 Phase 3.18 Runbook: Demo Trend Visualization Scope

## Purpose

Validate that trend insight pages can show clearly labeled demo trend data for competition demonstration while preserving Phase 3.17 real-data separation.

## Static Validation

Run on the cloud host:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
python -B -m py_compile \
  cloud_backend/postgres_repository.py \
  cloud_backend/teacher_pages.py \
  cloud_backend/admin_pages.py \
  cloud_backend/auth.py
bash -n scripts/validate_phase3_18_demo_trend_visualization_scope.sh
```

## Demo Data Preparation

Check whether demo trend data exists through the validation script. If it reports `PHASE318_TEACHER_TRENDS_DEMO_DATA_AVAILABLE=false`, seed demo data with:

```bash
cd /root/video_project_src
API_BASE_URL="http://127.0.0.1:8011" bash scripts/seed_phase3_demo_trend_data.sh --seed
```

Do not run cleanup during competition preparation unless explicitly requested.

## Runtime Validation

Run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_18_demo_trend_visualization_scope.sh
```

If service reload is required, use the actual deployment method for port `8011`. Do not assume `classroom-cloud-backend.service` exists.

## Browser Check

Open as teacher:

```text
/teacher/trends?data_source=demo&limit=20
```

Verify:

- The page clearly says demo data is only for demonstration.
- Teaching feedback trend chart is visible.
- Attention/activity chart is visible.
- Question/response chart is visible.
- Teaching stage chart is visible.
- Risk/priority list and recommendations are present when data supports them.

Open as admin:

```text
/admin/trends?data_source=demo&limit=30
```

Verify:

- Demo scope is clear.
- Overview and ranking sections render.

## Expected Markers

```text
PHASE318_DEMO_TREND_SEED_SCRIPT_PRESENT=true
PHASE318_TEACHER_TRENDS_DEMO_PAGE_REACHABLE=true
PHASE318_TEACHER_TRENDS_DEMO_WARNING_VISIBLE=true
PHASE318_TEACHER_TRENDS_DEMO_API_OK=true
PHASE318_TEACHER_TRENDS_DEMO_DATA_AVAILABLE=true
PHASE318_TEACHER_TRENDS_DEMO_SERIES_OK=true
PHASE318_TEACHER_TRENDS_DEMO_CHARTS_PRESENT=true
PHASE318_TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT=true
PHASE318_ADMIN_TRENDS_DEMO_API_OK=true
PHASE318_ADMIN_TRENDS_DEMO_SCOPE_OK=true
PHASE318_REAL_TRENDS_SCOPE_STILL_REAL=true
PHASE318_REPORTS_DEFAULT_NOT_DEMO=true
PHASE318_PHASE314_FINAL_SAMPLE_UNCHANGED=true
PHASE318_NO_DEMO_AS_REAL_CLAIM=true
PHASE318_DEMO_TREND_VISUALIZATION_READY=true
```

## Boundaries

- Demo trend data is for visualization and analysis capability demonstration.
- Real classroom analysis remains Phase 3.14 final sample plus eligible real records.
- No database deletion.
- No fake real metrics.
- No local analyzer, Raspberry Pi, or core algorithm changes.
- No git commit.
