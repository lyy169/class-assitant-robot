# Cloud Runtime Hardening Iteration 02

## 1. Goal

Document and harden the current source-side runtime for the cloud backend without changing API routes, dashboard structure, or storage semantics.

This iteration is limited to:

- formalizing the `8011` deployment runbook
- fixing source-side startup artifacts to point at `/root/video_project_src`
- making the `sqlite + raw` runtime shape explicit
- separating SSHFS-side preparation from Linux-server execution

## 2. Modified Files

- `cloud_backend/main.py`
- `cloud_backend/.env.runtime.example`
- `cloud_backend/classroom-cloud-backend.service.example`
- `cloud_backend/RUNBOOK.md`
- `scripts/deploy_cloud_backend.sh`
- `scripts/README.md`
- `docs/runbooks/cloud-runtime-and-sqlite-deploy-v1.md`
- `docs/project-status/cloud-runtime-hardening-iteration-02.md`

## 3. Runbook Path

Primary deployment runbook:

- `docs/runbooks/cloud-runtime-and-sqlite-deploy-v1.md`

## 4. Current Formal Runtime Port

Current formal source-side runtime port:

- `8011`

Important distinction:

- code default in `cloud_backend/config.py` remains `8010`
- formal deployment target is `8011` through `.env.runtime`

## 5. Current Formal Backend Choice

Current formal backend choice for source-side deployment:

- `sqlite`

Important distinction:

- code default in `cloud_backend/config.py` remains `file`
- formal deployment target is `sqlite` through:
  - `CLOUD_DB_BACKEND=sqlite`
  - `CLOUD_DATABASE_URL=/root/video_project_src/cloud_backend/data/cloud_results.sqlite3`

Current durability floor remains:

- raw JSON file persistence under `cloud_backend/data/raw/`

## 6. Runtime Hardening Added in This Iteration

### 6.1 Backend observability

`cloud_backend/main.py` now logs:

```text
Cloud query repository backend=<backend_name>
```

This is the minimal runtime signal for confirming whether the service actually started in `sqlite` mode or fell back to `file`.

### 6.2 Runtime env example

`cloud_backend/.env.runtime.example` now captures the current formal source-side runtime:

- `8011`
- `/root/video_project_src`
- `sqlite`
- source-side raw/data/sample paths

### 6.3 Startup helper alignment

`scripts/deploy_cloud_backend.sh` now targets:

- `/root/video_project_src`
- `/root/venv`
- `cloud_backend/.env.runtime`
- `uvicorn ... --port 8011`

### 6.4 Service example alignment

`cloud_backend/classroom-cloud-backend.service.example` now targets:

- `WorkingDirectory=/root/video_project_src`
- `EnvironmentFile=-/root/video_project_src/cloud_backend/.env.runtime`
- `ExecStart=... --port 8011`

## 7. Validation Completed Under SSHFS

The following validation was completed from the mounted workspace only:

- checked current config defaults in `cloud_backend/config.py`
- checked current repository selection and raw-first write path in `cloud_backend/storage.py`
- checked current app wiring in `cloud_backend/main.py`
- confirmed the new runtime env example points to `8011 + sqlite`
- confirmed the startup helper script and service example now point to the source-side repository instead of `/root/video_project`
- confirmed the authoritative deployment steps were consolidated into the new runbook

The following was not executed under SSHFS and therefore is not claimed as completed:

- starting the service on the Linux server
- confirming a live listener on `8011`
- curling the live service
- installing or enabling a systemd unit

## 8. Operator-Reported Live Validation on 2026-04-20

The following evidence was provided by the operator from the Linux server after switching startup to:

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

### 8.1 Source-side service startup succeeded

Observed runtime output included:

- `CLOUD_PORT=8011`
- `CLOUD_DB_BACKEND=sqlite`
- `Cloud query repository backend=sqlite`
- `Uvicorn running on http://0.0.0.0:8011`

Current conclusion:

- the source-side formal runtime started successfully on `8011`
- the query backend was not in fallback `file` mode
- the process was started with the intended `.env.runtime` configuration

### 8.2 SQLite file exists at the formal path

Observed command:

```bash
ls -l /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

Observed result:

```text
-rw-r--r-- 1 root root 12288 Apr 20 19:39 /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

Current conclusion:

- the formal SQLite file exists
- the configured database path is valid and writable enough for runtime creation

### 8.3 Raw fallback directory contains real files

Observed command:

```bash
find /root/video_project_src/cloud_backend/data/raw -maxdepth 2 -type f | sort
```

Observed result:

```text
/root/video_project_src/cloud_backend/data/raw/2026-04-19/cls_20260417_101_001.json
/root/video_project_src/cloud_backend/data/raw/2026-04-20/classroom_20260417_001.json
/root/video_project_src/cloud_backend/data/raw/2026-04-20/cls_20260417_101_001.json
```

Current conclusion:

- raw fallback persistence is present on disk
- the source-side runtime is not SQLite-only
- previously uploaded or validated records remain visible in the raw floor

### 8.4 Live verification boundary still kept explicit

The following items are now confirmed in live runtime evidence:

- source-side startup on `8011`
- runtime backend selection `sqlite`
- SQLite file existence
- raw file existence
- fresh `GET /health` returned `200`
- fresh `GET /api/recent-interaction-results?limit=5&classroom_id=classroom_101` returned `200`
- fresh `GET /dashboard?classroom_id=classroom_101&limit=5` returned `200`
- fresh recent payload reported `fallback_to_sample=false`
- fresh recent payload reported `source_kind=raw`
- fresh recent payload reported `analysis_id=cls_20260417_101_001`
- fresh dashboard HTML reported `Teacher Results Center`
- fresh dashboard HTML reported `classroom_101`
- fresh dashboard HTML reported `raspberrypi-01`
- fresh dashboard HTML reported `Response Score` value `16.36`
- fresh dashboard HTML reported recent rows with `<span class="badge">raw</span>`
- fresh dashboard HTML reported recent row `cls_20260417_101_001`

Observed `health` response after final `sqlite` startup:

```text
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok"}
```

Observed `recent` response characteristics after final `sqlite` startup:

```text
HTTP/1.1 200 OK
content-type: application/json
success=true
classroom_id=classroom_101
fallback_to_sample=false
results[0].source_kind=raw
results[0].result.analysis_id=cls_20260417_101_001
results[0].source_path=/root/video_project_src/cloud_backend/data/raw/2026-04-20/cls_20260417_101_001.json
```

Observed `dashboard` response characteristics after final `sqlite` startup:

```text
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
title=Cloud Classroom Results Center
h1=Teacher Results Center
Classroom=classroom_101
Source Host=raspberrypi-01
Response Score=16.36
Recent Classroom Results includes cls_20260417_101_001
recent source badge=raw
```

Current conclusion:

- the final `sqlite` runtime has a complete fresh validation bundle for `health`, `recent`, and `dashboard`
- the dashboard is rendering real raw-backed classroom results rather than sample fallback
- the runtime mode has been corrected from `file` fallback to the intended `sqlite + raw` formal configuration

## 9. Commands the Operator Must Run on the Linux Server

Prepare runtime env file if needed:

```bash
cd /root/video_project_src
cp cloud_backend/.env.runtime.example cloud_backend/.env.runtime
```

Start the source-side service:

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

Check listener:

```bash
ss -lntp | grep 8011
```

Check health:

```bash
curl -i http://127.0.0.1:8011/health
```

Check recent:

```bash
curl -i "http://127.0.0.1:8011/api/recent-interaction-results?limit=5&classroom_id=classroom_101"
```

Check dashboard:

```bash
curl -i "http://127.0.0.1:8011/dashboard?classroom_id=classroom_101&limit=5"
```

Check SQLite file:

```bash
ls -l /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

Check raw write floor:

```bash
find /root/video_project_src/cloud_backend/data/raw -maxdepth 2 -type f | sort
```

## 10. Current Unfinished Items

- no systemd installation or enablement has been executed
- code defaults are still `8010 + file`, so runtime depends on `.env.runtime` being loaded correctly

## 11. Next-Step Suggestions

1. Decide whether to keep using the foreground startup script or install the aligned systemd unit.
2. If the current mode is accepted as formal, freeze `.env.runtime` and the startup path as the handoff baseline.
3. If needed, add one operator-facing runbook note for graceful stop/restart procedures on the Linux server.
