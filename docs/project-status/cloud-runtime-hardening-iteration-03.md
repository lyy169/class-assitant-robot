# Cloud Runtime Hardening Iteration 03

## 1. Goal

Add the minimum runtime observability and operator guidance for the upcoming continuous-upload scenario without changing API routes, dashboard structure, or storage logic.

This iteration is limited to:

- documenting continuous-upload checks
- documenting how to confirm recent/dashboard stay on real data paths
- adding one minimal operator observability script
- keeping SSHFS preparation and Linux-server execution clearly separated

## 2. Modified Files

- `docs/runbooks/cloud-runtime-and-sqlite-deploy-v1.md`
- `docs/project-status/cloud-runtime-hardening-iteration-03.md`
- `scripts/check_cloud_runtime_observability.sh`
- `scripts/README.md`

## 3. Runbook Path

Primary runbook updated in this iteration:

- `docs/runbooks/cloud-runtime-and-sqlite-deploy-v1.md`

## 4. New Minimum Operational Checks

This iteration adds the following continuous-upload checks:

- confirm the service is still listening on `8011`
- confirm runtime mode is still `sqlite`, not fallback `file`
- confirm `recent` keeps returning `fallback_to_sample=false`
- confirm newest rows in `recent` keep returning `source_kind=raw`
- confirm a newly expected `analysis_id` appears in:
  - `recent`
  - raw file storage
  - dashboard HTML
- confirm SQLite file still exists and remains non-empty
- confirm raw write floor still contains recent files

## 5. Operator Commands

The following commands must be executed by the operator on the Linux server.

Basic continuous-upload check:

```bash
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

Classroom-filtered check:

```bash
cd /root/video_project_src
CLASSROOM_ID=classroom_101 LIMIT=10 bash scripts/check_cloud_runtime_observability.sh
```

Check for a specific expected upload:

```bash
cd /root/video_project_src
CLASSROOM_ID=classroom_101 EXPECT_ANALYSIS_ID=cls_20260417_101_001 bash scripts/check_cloud_runtime_observability.sh
```

Manual API checks if the operator does not want to use the script:

```bash
curl -s "http://127.0.0.1:8011/api/recent-interaction-results?limit=10&classroom_id=classroom_101"
curl -s "http://127.0.0.1:8011/dashboard?classroom_id=classroom_101&limit=10"
find /root/video_project_src/cloud_backend/data/raw -maxdepth 2 -type f | sort | tail -n 10
ls -lh /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

Optional SQLite row check:

```bash
sqlite3 /root/video_project_src/cloud_backend/data/cloud_results.sqlite3 \
  "select analysis_id, classroom_id, source_kind, generated_at from classroom_results order by generated_at desc, created_at desc limit 10;"
```

## 6. Current Continuous-Upload Observation Method

Current minimum observation method is:

1. query `recent`
2. verify `fallback_to_sample=false`
3. verify newest rows use `source_kind=raw`
4. verify the newest `analysis_id` also exists under `cloud_backend/data/raw/`
5. verify dashboard HTML still contains the same `analysis_id` and `raw` badge
6. optionally verify the same `analysis_id` exists in SQLite

Current helper script support:

- `scripts/check_cloud_runtime_observability.sh`

What it checks:

- SQLite file presence
- recent raw file list
- recent API payload summary
- expected `analysis_id` hit or miss
- dashboard HTML markers
- optional SQLite row output if `sqlite3` is installed

## 7. Validation Completed Under SSHFS

The following validation was completed from the mounted workspace only:

- checked that the new runbook section matches the current implementation shape:
  - `recent` and `dashboard` remain current observability surfaces
  - raw write path remains `cloud_backend/data/raw/`
  - SQLite path remains `cloud_backend/data/cloud_results.sqlite3`
- checked that the helper script only reads runtime state and does not mutate service state
- checked that the helper script parameters match the current deployment assumptions:
  - `API_BASE_URL=http://127.0.0.1:8011`
  - `CLOUD_SRC_DIR=/root/video_project_src`
- checked that the script and runbook explicitly require Linux-server execution for live verification

The following was not executed under SSHFS and is therefore not claimed as completed:

- producing the live baseline output locally from the mounted workspace
- confirming live SQLite row output via `sqlite3`

## 8. Current Unfinished Items

- the baseline has been verified from operator-provided Linux-server output, but no classroom-filtered baseline has been captured yet
- no process-manager level rotation or restart guidance has been added beyond the current runbook
- no alerting or automated retention policy exists yet for long-running upload operations

## 9. Next-Step Suggestions

1. If needed, capture one classroom-filtered baseline with `CLASSROOM_ID=classroom_101`.
2. Decide whether the current foreground runtime should remain operator-managed or move to systemd as the formal steady-state mode.
3. If uploads become frequent, add one operator note for log review and one retention rule for old raw files and SQLite backups.
