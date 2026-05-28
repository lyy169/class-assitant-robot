# Cloud Backend Runbook

## Position

`cloud_backend/` is the formal cloud mainline for classroom interaction result ingestion and teacher-facing result viewing.

It is responsible for:

- receiving JSON pushed from the local analysis workstation
- validating request payloads against classroom feedback JSON schema `v1.1`
- logging structured request activity
- persisting raw classroom interaction JSON
- exposing latest and recent read-back routes
- rendering the minimal teacher-facing results center

It is not responsible for:

- old Flask login pages
- old Flask video page flow
- old Flask history page flow
- direct MP4 and video page integration in the current round

## Current Endpoints

- `GET /health`
- `POST /api/interaction-results`
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /dashboard`

## Operational Meaning

- `/health`
  - liveness check for smoke tests and supervision
- `/api/interaction-results`
  - formal ingestion endpoint for classroom interaction result JSON
- `/api/latest-interaction-result`
  - latest readable result, with optional `classroom_id`
- `/api/recent-interaction-results`
  - recent result list, with optional `classroom_id` and `limit`
- `/dashboard`
  - minimal teacher-facing results center

## Startup

The authoritative deployment instructions for the source-side `8011` service are maintained in:

- `docs/runbooks/cloud-runtime-and-sqlite-deploy-v1.md`

Use that runbook for:

- `.env.runtime` preparation
- `8011` startup
- SQLite query backend configuration
- raw fallback write-path verification
- SSHFS-safe operator steps that must be run on the Linux server

## Result Read Order

For latest and recent queries:

1. matching raw JSON under `cloud_backend/data/raw/`
2. fallback sample JSON under `cloud_backend/sample_data/`

This means the source-side results center can still be demonstrated safely when no raw classroom data has been pushed yet.

## Payload Contract

The only accepted payload standard for this stage is classroom feedback JSON schema `v1.1`.

Key protocol groups:

- `schema_version`
- `analysis_id`, `classroom_id`, `video_id`
- `source`
- `time`
- `summary`
- `teacher`
- `students`
- `timeline`

## Dashboard Scope

The current `/dashboard` includes:

- latest classroom overview card
- recent result list
- simple classroom filter input
- latest region / heat summary
- latest interaction breakdown
- system note for future MP4 and video archive support

This is a teacher-facing prototype, not yet the final production dashboard.

## Data Persistence

Current runtime persistence path:

```text
cloud_backend/data/raw/YYYY-MM-DD/<window_id>.json
```

Current source-side sample path:

```text
cloud_backend/sample_data/
```

The runtime data path must stay outside Git management.

## Environment Variable Categories

Recommended `.env` categories:

- service base config
  - app name
  - host
  - port
  - debug
  - log level
- storage config
  - data directory
  - raw JSON directory
  - sample data directory
- auth config
  - API key required or not
  - API key value
  - API key header name
- business validation config
  - `classroom_id` required or not
  - `source_host` required or not
- future data backend config
  - backend type
  - database URL

## Logging Guidance

Recommended split:

- process logs handled by `systemd` or `supervisor`
- application logs containing `request_id`, client source, `classroom_id`, `window_id`, and save path

Suggested future file-log location if needed:

```text
/root/video_project/logs/cloud_backend/
```

Do not change active online logging paths in the current round.

## Validation

Use:

- `docs/runbooks/cloud-results-dashboard-runbook.md`
- `docs/runbooks/cloud-results-center-validation-runbook.md`
- `scripts/validate_cloud_results_center.sh`

## Future Integration Boundary

MP4 upload and video browsing remain preserved capabilities.

Planned role:

- `dashboard` remains the top-level teacher results center
- MP4 and video archive views later join as supporting teacher-facing modules
- old Flask pages remain legacy references until a later integration round
