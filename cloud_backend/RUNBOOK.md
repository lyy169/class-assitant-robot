# Cloud Backend Runbook

## Position

`cloud_backend/` is the current formal cloud mainline for classroom interaction result ingestion.

It is responsible for:
- receiving JSON pushed from the local YOLO workstation
- validating the request payload at a minimal business-safe level
- recording structured logs
- persisting raw result files

It is not responsible for:
- old Flask login pages
- old Flask history pages
- old Flask video page flow
- the MP4 upload main chain

## Interface Boundary

Current endpoints:
- `GET /health`
- `POST /api/interaction-results`

Operational meaning:
- `/health` is the liveness check for process supervision and smoke verification
- `/api/interaction-results` is the formal ingestion endpoint for classroom interaction result JSON

## Startup

Typical manual startup from the deployment copy:

```bash
cd /root/video_project
source /root/venv/bin/activate
pip install -r cloud_backend/requirements.txt
uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8010
```

Notes:
- keep the current deployment directory unchanged
- do not combine startup changes with Git bootstrap changes
- use a dedicated `.env` when moving toward formal supervision

## Health Check

Recommended verification:

```bash
curl http://127.0.0.1:8010/health
```

Expected response:

```json
{"status":"ok"}
```

## Ingestion Endpoint

Primary endpoint:

```text
POST /api/interaction-results
```

Current behavior:
- accepts JSON object payloads
- accepts direct payload or envelope-with-`payload`
- optionally checks `X-API-Key`
- validates business fields such as `classroom_id` and `source_host` when required by configuration
- writes raw JSON to disk

## Data Persistence Path

Current raw result path:

```text
cloud_backend/data/raw/YYYY-MM-DD/<window_id>.json
```

This path is deployment runtime data and must not be included in the first source-managed Git bootstrap.

## Environment Variable Categories

Real `.env` values should be grouped by category:

- service base config
  - app name
  - host
  - port
  - debug
  - log level
- storage config
  - data directory
  - raw JSON directory
- auth config
  - whether API key is required
  - API key value
  - header name
- business validation config
  - whether `classroom_id` is required
  - whether `source_host` is required
- future data backend config
  - backend type
  - database URL

## Logging Guidance

Recommended split:
- process logs collected by `systemd` or `supervisor`
- application logs containing request source, `request_id`, `window_id`, saved path, and exception details

Suggested future log location if file logs are introduced:

```text
/root/video_project/logs/cloud_backend/
```

This is a future recommendation only. Do not change the active online logging path in the current round.

## Future Supervision

Preferred future supervision order:
1. `systemd`
2. `supervisor` if the server remains standardized on it

Supervision requirements:
- clear working directory
- dedicated `EnvironmentFile`
- explicit service name
- automatic restart only for abnormal process exit
- no hidden coupling with old Flask service names

Recommended service name:
- `classroom-cloud-backend.service`

## Source Vs Deploy Boundary

Current deployment boundary:
- deployment copy: `video_project/`
- runtime data: `cloud_backend/data/`
- runtime logs: `logs/`

Future source boundary:
- separate source directory: `video_project_src/`
- first managed assets: `cloud_backend/`, `docs/`, `scripts/`

Do not treat the current deployment copy as the clean source repository before the separate source directory exists.
