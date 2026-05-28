# Cloud Results Center Validation Runbook

## Purpose

This runbook explains how to validate the recent-results center from a real cloud terminal without touching the running deployment directory.

## Preconditions

Before running validation:

1. start the source-side app from `/root/video_project_src`
2. use a non-production test port such as `8011`
3. make sure the cloud security group and host firewall both allow that port if browser access is needed

Example startup:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8011
```

## Validation Script

Run:

```bash
cd /root/video_project_src
bash scripts/validate_cloud_results_center.sh
```

Optional environment overrides:

```bash
BASE_URL="http://127.0.0.1:8011" CLASSROOM_ID="classroom_101" bash scripts/validate_cloud_results_center.sh
```

## What The Script Checks

- `GET /health`
- `GET /api/recent-interaction-results`
- `GET /api/recent-interaction-results?classroom_id=classroom_101`
- `GET /dashboard?classroom_id=classroom_101`
- dashboard HTML markers for overview, recent list, filter, and heat summary

## What To Verify Manually In Browser

Open:

```text
http://<server-ip>:8011/dashboard
http://<server-ip>:8011/dashboard?classroom_id=classroom_101
```

Confirm that the page shows:

- latest classroom overview
- recent result list
- classroom filter input
- region / heat summary
- short system note about MP4 and video archive support later

## Validation Boundary

Current validation may use sample data when no raw classroom results are available.

This is acceptable for this round because:

- the goal is route and display verification
- file-backed recent queries are now the focus
- real classroom data can be layered in later without changing the route contract

## If Validation Fails

Check in this order:

1. the source-side app is really started from `/root/video_project_src`
2. the chosen test port is listening
3. the security group allows the test port
4. the host firewall allows the test port
5. sample data still exists under `cloud_backend/sample_data/`
