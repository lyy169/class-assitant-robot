# V3 Phase 3.0 Spec: Teaching Trends And Classroom Report Center

## 1. Purpose

Phase 3.0 upgrades the platform from single-classroom result viewing to longitudinal teaching analysis.

Goal:

```text
teacher trends
classroom reports
admin trend overview
rule-based teaching recommendations
optional AI summary
demo trend data without polluting real analysis
```

This phase should support competition demonstration while preserving data credibility.

## 2. Confirmed Scope

In scope:

- `/teacher/trends`
- `/teacher/reports`
- `/admin/trends`
- `GET /api/teacher/trends`
- `GET /api/teacher/reports`
- `GET /api/teacher/reports/detail`
- `POST /api/teacher/reports/ai-summary`
- `GET /api/admin/trends`
- rule-based report generation
- optional AI single-lesson summary
- demo trend seed/cleanup script
- real/demo data source filtering
- validation script

Out of scope:

- PDF export
- Excel export
- email delivery
- AI summary cache
- report snapshot table
- trend AI summary
- student-level profile
- video asset hosting
- device upload authentication
- new data warehouse
- Raspberry Pi/local analyzer changes

## 3. Data Credibility Principle

Real and demo data must not be silently mixed.

Rules:

```text
default data_source = real
demo data must be explicitly marked
demo data must be explicitly selectable
demo/all views must show a visible warning
demo data must be seedable and cleanable
```

## 4. Dataset Marker

Phase 3.0 does not change existing raw JSON structure. It may add compatible metadata.

Real data:

```json
{
  "dataset": {
    "source": "real"
  }
}
```

Demo seed data:

```json
{
  "dataset": {
    "source": "demo",
    "purpose": "phase3_trend_seed",
    "generated_at": "2026-04-30T10:00:00+08:00"
  }
}
```

Compatibility:

```text
missing dataset.source -> real
dataset.source=real -> real
dataset.source=demo -> demo
other values -> unknown
```

Unknown data should not be included in `data_source=real` results.

## 5. Data Source Filter

Trend and report APIs support:

```text
data_source=real|demo|all
```

Default:

```text
real
```

Applies to:

- `GET /api/teacher/trends`
- `GET /api/teacher/reports`
- `GET /api/admin/trends`

Report detail returns the detected source as `dataset_source`.

## 6. Pages

### 6.1 Teacher Trends

Route:

```text
GET /teacher/trends
```

Purpose:

```text
Show a teacher how classroom performance changes over time.
```

Filters:

- `classroom_id`
- `date_from`
- `date_to`
- `data_source`
- `limit`

Default:

```text
last 30 days
data_source=real
limit=20
```

Required modules:

- overview metric cards
- score trend chart
- attention/activity trend chart
- question count / response rate trend chart
- stage structure chart
- risk lesson list
- rule recommendations
- data source warning
- insufficient real-data empty state

### 6.2 Teacher Reports

Route:

```text
GET /teacher/reports
GET /teacher/reports?result_id=<result_id>
```

No `result_id`:

- report list mode

With `result_id`:

- report detail mode

List modules:

- filters
- report cards/table
- score
- attention/activity
- question count
- risk level
- dataset source tag
- open report
- open dashboard

Detail modules:

- basic lesson info
- overall score
- attention/activity curves
- stage structure
- teacher question and response analysis
- issues
- highlights
- risks
- rule-based recommendations
- optional AI summary area
- open original dashboard

### 6.3 Admin Trends

Route:

```text
GET /admin/trends
```

Purpose:

```text
Show global teaching trend and risk overview for administrators.
```

Filters:

- `classroom_id`
- `teacher_id`
- `date_from`
- `date_to`
- `data_source`
- `limit`

Required modules:

- platform overview cards
- classroom ranking
- teacher activity ranking
- low-score risk lessons
- recent report summary
- data source warning

## 7. APIs

### 7.1 Teacher Trends

```text
GET /api/teacher/trends
```

Parameters:

- `classroom_id`
- `date_from`
- `date_to`
- `data_source`
- `limit`

Response:

```json
{
  "success": true,
  "filters": {},
  "overview": {},
  "series": {},
  "stage_distribution": {},
  "risk_lessons": [],
  "recommendations": [],
  "data_quality": {}
}
```

### 7.2 Teacher Reports

```text
GET /api/teacher/reports
```

Parameters:

- `classroom_id`
- `date_from`
- `date_to`
- `data_source`
- `limit`

Response:

```json
{
  "success": true,
  "filters": {},
  "items": []
}
```

### 7.3 Teacher Report Detail

```text
GET /api/teacher/reports/detail?result_id=<result_id>
```

Response:

```json
{
  "success": true,
  "report": {
    "basic": {},
    "scores": {},
    "timeline": {},
    "stage_distribution": {},
    "question_analysis": {},
    "issues": [],
    "highlights": [],
    "risks": [],
    "recommendations": [],
    "ai_summary": {
      "enabled": false,
      "status": "not_configured",
      "content": ""
    },
    "dataset_source": "real",
    "dashboard_url": "/dashboard?result_id=..."
  }
}
```

### 7.4 AI Summary

```text
POST /api/teacher/reports/ai-summary
```

Request:

```json
{
  "result_id": "cls_xxx"
}
```

Success:

```json
{
  "success": true,
  "ai_summary": {
    "enabled": true,
    "status": "success",
    "content": "..."
  }
}
```

Failure:

```json
{
  "success": false,
  "ai_summary": {
    "enabled": true,
    "status": "failed",
    "content": "",
    "error": "timeout"
  }
}
```

### 7.5 Admin Trends

```text
GET /api/admin/trends
```

Parameters:

- `classroom_id`
- `teacher_id`
- `date_from`
- `date_to`
- `data_source`
- `limit`

Response:

```json
{
  "success": true,
  "filters": {},
  "overview": {},
  "classroom_rankings": [],
  "teacher_activity": [],
  "risk_lessons": [],
  "recent_reports": [],
  "data_quality": {}
}
```

## 8. Aggregation Rules

Use existing data:

- `analysis_results`
- `payload_json`
- `created_at`
- `classroom_id`
- `score`
- `status`

Do not add trend/report tables in Phase 3.0.

Default status behavior:

```text
include raw + reviewed
exclude archived
```

Per-lesson extracted fields:

- result_id
- classroom_id
- classroom_name
- lesson_title
- created_at
- score
- attention_score
- activity_score
- question_count
- response_rate
- discussion_ratio
- exposition_ratio
- management_ratio
- summary_ratio
- issue_count
- event_count
- dataset_source

Compatibility:

- `score` / `overall_score`
- `created_at` / `timestamp` / `time.generated_at`
- `timeline.attention_curve`
- `timeline.activity_curve`
- `teacher.question_events`
- `events` / `issues`
- summary ratios

## 9. Rule-Based Report

Rules generate:

- highlights
- risks
- recommendations
- risk level

Examples:

```text
low attention -> increase interaction rhythm
low activity -> add group discussion or short exercises
low question count -> add guiding questions
low response rate -> extend wait time and follow-up prompts
high management ratio -> optimize classroom organization
high issue count -> focus on participation and order
```

Rule report is mandatory and must work without AI.

## 10. Optional AI Summary

AI is optional enhancement, not a hard dependency.

AI only summarizes structured report data. It does not compute metrics.

Trigger:

```text
button click on report detail page
```

Scope:

```text
single-lesson report only
```

No cache in Phase 3.0.

Configuration:

```text
AI_REPORT_ENABLED=true/false
AI_REPORT_PROVIDER=deepseek
AI_REPORT_API_KEY=...
AI_REPORT_MODEL=...
AI_REPORT_TIMEOUT=20
```

If AI is not configured or fails:

```text
rule report remains visible
AI area reports not_configured or failed
```

Prompt input must be structured summary, not full raw JSON.

Output:

```text
Chinese
200-300 words
professional and constructive
must not invent unsupported facts
```

## 11. Demo Trend Seed

Add:

```text
scripts/seed_phase3_demo_trend_data.sh
```

Commands:

```bash
bash scripts/seed_phase3_demo_trend_data.sh --seed
bash scripts/seed_phase3_demo_trend_data.sh --cleanup
```

Rules:

- generate 6-10 `demo_phase3_*` results
- use `dataset.source=demo`
- use `dataset.purpose=phase3_trend_seed`
- upload through existing `POST /api/interaction-results`
- cleanup demo records without touching real data

## 12. Permissions

Use Phase 2.9 permission model:

```text
teacher -> bound classrooms only
admin -> global
```

AI summary endpoint must enforce the same result visibility rules.

## 13. Navigation

Teacher navigation adds:

```text
Trends
Reports
```

Admin navigation adds:

```text
Trends
```

## 14. Compatibility

Preserve:

- Phase 2.9 login and role boundary
- Phase 2.8.1 ingestion status
- Phase 2.5 dashboard
- `POST /api/interaction-results`
- raw JSON compatibility

