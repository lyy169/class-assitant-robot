# Cloud Results Dashboard Runbook

## Purpose

This runbook explains how to access and validate the cloud-side teacher results center in `cloud_backend/`.

The payload contract for ingestion, storage, and display is classroom feedback JSON schema `v1.1`.

## Available Endpoints

- `GET /health`
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /dashboard`
- `POST /api/interaction-results`

## How To Access

Teacher-facing page:

```text
http://<host>:<port>/dashboard
```

Latest result JSON:

```text
http://<host>:<port>/api/latest-interaction-result
```

Recent results JSON:

```text
http://<host>:<port>/api/recent-interaction-results
```

Classroom-filtered examples:

```text
http://<host>:<port>/api/recent-interaction-results?classroom_id=classroom_101
http://<host>:<port>/dashboard?classroom_id=classroom_101
```

## Current Data Source

Read order:

1. matching raw JSON under `cloud_backend/data/raw/`
2. fallback sample JSON under `cloud_backend/sample_data/`

Behavior note:

- when no raw results are available, the recent query and dashboard fall back to sample data
- the API response includes `source_kind`
- the dashboard note also explains whether the view is reading raw or sample data

## Current Dashboard Modules

The current dashboard is now a minimal teacher results center with:

- latest classroom overview card
- recent N result table
- simple `classroom_id` filter
- teacher question event list
- stage distribution
- zone summary
- timeline curves
- system note about future MP4 and video archive integration

## Current Limitations

- current history query is still file-based
- current filter is only `classroom_id`
- no pagination yet
- no `analysis_id` detail page yet
- no database-backed trend queries yet
- MP4 and video browsing are not integrated into this page in the current round

## Validation Approach

For quick source-side validation:

1. start `uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8011`
2. call `/api/recent-interaction-results`
3. call `/api/recent-interaction-results?classroom_id=classroom_101`
4. open `/dashboard`
5. confirm the page shows overview, recent list, filter, and heat summary

If you want a scripted terminal check, use:

```text
scripts/validate_cloud_results_center.sh
```

And see:

```text
docs/runbooks/cloud-results-center-validation-runbook.md
```

## Future Direction

Recommended next direction:

1. keep the current routes stable
2. add recent-result detail and trend views
3. introduce a database-backed repository
4. link MP4 and video archive assets as supporting teacher-facing modules
