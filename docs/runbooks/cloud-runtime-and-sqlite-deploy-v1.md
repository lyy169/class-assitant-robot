# Cloud Runtime and SQLite Deploy V1

## Scope

This runbook documents the current source-side runtime for the cloud backend under the SSHFS workflow.

It is based on the current implementation in:

- `cloud_backend/config.py`
- `cloud_backend/main.py`
- `cloud_backend/storage.py`
- `cloud_backend/.env.runtime.example`
- `scripts/deploy_cloud_backend.sh`
- `cloud_backend/classroom-cloud-backend.service.example`

It does not claim that service startup, port listening, or process-manager installation has already been executed on the Linux server.

## 1. Current formal runtime target

Current formal source-side runtime target:

- source repository: `/root/video_project_src`
- app entry: `cloud_backend.main:app`
- formal listener port: `8011`
- formal query backend: `sqlite`
- raw write floor: enabled

Important distinction:

- code defaults in `cloud_backend/config.py` are still:
  - `CLOUD_PORT=8010`
  - `CLOUD_DB_BACKEND=file`
- formal deployment for the source-side service is defined by loading `cloud_backend/.env.runtime`, which should mirror `cloud_backend/.env.runtime.example`

If the env file is not loaded, the service falls back to code defaults and recent/latest will query from the file repository instead of SQLite.

## 2. Formal runtime configuration

Recommended runtime env file path:

```text
/root/video_project_src/cloud_backend/.env.runtime
```

Example source file already present in the repo:

```text
/root/video_project_src/cloud_backend/.env.runtime.example
```

Current formal env values:

```dotenv
CLOUD_APP_NAME="Classroom Interaction Cloud Backend"
CLOUD_HOST=0.0.0.0
CLOUD_PORT=8011
CLOUD_DATA_DIR=/root/video_project_src/cloud_backend/data
CLOUD_RAW_DIR=/root/video_project_src/cloud_backend/data/raw
CLOUD_SAMPLE_DATA_DIR=/root/video_project_src/cloud_backend/sample_data
CLOUD_DB_BACKEND=sqlite
CLOUD_DATABASE_URL=/root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

Note:

- values containing spaces must be quoted in `.env.runtime`
- `CLOUD_APP_NAME="Classroom Interaction Cloud Backend"` is valid
- `CLOUD_APP_NAME=Classroom Interaction Cloud Backend` will break `source`

Optional validation toggles already supported by code:

```dotenv
CLOUD_REQUIRE_API_KEY=false
CLOUD_REQUIRE_CLASSROOM_ID=true
CLOUD_REQUIRE_SOURCE_HOST=true
```

## 3. Current formal startup command

Preferred manual startup command on the Linux server:

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

That helper script:

1. activates `/root/venv`
2. loads `/root/video_project_src/cloud_backend/.env.runtime` when present
3. installs Python dependencies from `cloud_backend/requirements.txt`
4. starts `uvicorn cloud_backend.main:app`

Direct equivalent command if you do not want to use the helper script:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
set -a
source /root/video_project_src/cloud_backend/.env.runtime
set +a
pip install -r cloud_backend/requirements.txt
uvicorn cloud_backend.main:app --host "${CLOUD_HOST:-0.0.0.0}" --port "${CLOUD_PORT:-8011}"
```

## 4. Dashboard and formal API addresses

When the service is running on the current formal source-side port, the address pattern is:

- dashboard:
  - `http://<SERVER_IP>:8011/dashboard`
- dashboard with classroom filter:
  - `http://<SERVER_IP>:8011/dashboard?classroom_id=classroom_101&limit=5`
- health:
  - `http://<SERVER_IP>:8011/health`
- formal ingestion entry:
  - `http://<SERVER_IP>:8011/api/interaction-results`
- latest:
  - `http://<SERVER_IP>:8011/api/latest-interaction-result`
- recent:
  - `http://<SERVER_IP>:8011/api/recent-interaction-results?limit=5`

## 5. Current backend selection behavior

Current write path in `cloud_backend/main.py`:

1. validate request payload against `schemas_v11.py`
2. persist raw JSON through `FileResultRepository`
3. if the active query backend is not the raw repository, index the same payload into the query repository

Current query repository selection in `cloud_backend/storage.py`:

- `CLOUD_DB_BACKEND=sqlite`
  - use `SQLiteResultRepository`
- any other value or missing env
  - use `FileResultRepository`

Current runtime observability:

- startup logs now print:
  - `Cloud query repository backend=<backend_name>`

This line is emitted from `cloud_backend/main.py` during app startup and should be checked in the foreground console output or in the process-manager log.

## 6. Current recent/latest source of truth

Current code behavior:

- code default without env override:
  - recent/latest run on `FileResultRepository`
- formal deployment target with `.env.runtime` loaded:
  - recent/latest run on `SQLiteResultRepository`

SQLite repository behavior:

- reads recent/latest/detail from SQLite when rows exist
- falls back to file-based recent/latest/detail when SQLite is empty or unavailable

This means the current formal runtime is:

- query and index path: SQLite
- durability floor: raw JSON file persistence

## 7. Raw fallback write path

Current formal raw path:

```text
/root/video_project_src/cloud_backend/data/raw/YYYY-MM-DD/<analysis_id>.json
```

Current formal SQLite file path:

```text
/root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

The raw write path remains the hard floor. SQLite indexing does not replace raw persistence.

## 8. Server-side preparation steps

The following steps must be executed by the operator on the Linux server, not through SSHFS alone.

### 8.1 Prepare runtime env file

If `.env.runtime` does not exist yet:

```bash
cd /root/video_project_src
cp cloud_backend/.env.runtime.example cloud_backend/.env.runtime
```

Then review the values in:

```text
/root/video_project_src/cloud_backend/.env.runtime
```

### 8.2 Start the source-side service

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

### 8.3 Optional systemd service setup

Example unit file in the repo:

```text
/root/video_project_src/cloud_backend/classroom-cloud-backend.service.example
```

If you later adopt systemd, copy and adapt that file on the Linux server. Do not treat the example file as already installed.

## 9. Availability verification commands

These commands must be run by the operator on the Linux server after startup.

### 9.1 Check listener

```bash
ss -lntp | grep 8011
```

### 9.2 Check health

```bash
curl -i http://127.0.0.1:8011/health
```

Expected:

- HTTP `200`
- body contains `{"status":"ok"}` or equivalent JSON with `status=ok`

### 9.3 Check latest

```bash
curl -i "http://127.0.0.1:8011/api/latest-interaction-result?classroom_id=classroom_101"
```

### 9.4 Check recent

```bash
curl -i "http://127.0.0.1:8011/api/recent-interaction-results?limit=5&classroom_id=classroom_101"
```

Verification points:

- HTTP `200`
- payload contains `results`
- `source_kind` should be `raw` for real uploaded records
- the returned `analysis_id` should match the uploaded record

### 9.5 Check dashboard

```bash
curl -i "http://127.0.0.1:8011/dashboard?classroom_id=classroom_101&limit=5"
```

Browser access pattern:

```text
http://<SERVER_IP>:8011/dashboard?classroom_id=classroom_101&limit=5
```

### 9.6 Check SQLite file

```bash
ls -l /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

Optional row check if `sqlite3` CLI is installed:

```bash
sqlite3 /root/video_project_src/cloud_backend/data/cloud_results.sqlite3 \
  "select analysis_id, classroom_id, source_kind, generated_at from classroom_results order by generated_at desc, created_at desc limit 5;"
```

### 9.7 Check raw write floor

```bash
find /root/video_project_src/cloud_backend/data/raw -maxdepth 2 -type f | sort
```

## 10. Continuous Upload Operations

This section is for the upcoming steady-state mode where the local workstation or Raspberry Pi side keeps uploading new classroom analysis results over time.

### 10.1 What to watch in continuous upload mode

Minimum operator checks:

- the service is still listening on `8011`
- startup mode is still `sqlite`, not fallback `file`
- `recent` continues to return `fallback_to_sample=false`
- `recent` continues to return `source_kind=raw` for the newest records
- the newest `analysis_id` appears in both:
  - `GET /api/recent-interaction-results`
  - raw file storage under `cloud_backend/data/raw/`
- dashboard still renders the same latest real result instead of sample fallback
- SQLite file still exists and remains non-empty

### 10.2 How to confirm recent still comes from real runtime data

Run on the Linux server:

```bash
curl -s "http://127.0.0.1:8011/api/recent-interaction-results?limit=5&classroom_id=classroom_101"
```

Expected characteristics:

- `success=true`
- `fallback_to_sample=false`
- newest rows show `source_kind=raw`
- `source_path` points into:

```text
/root/video_project_src/cloud_backend/data/raw/YYYY-MM-DD/
```

If `fallback_to_sample=true` or newest rows show `source_kind=sample`, then the runtime is no longer reading the real upload path as expected.

### 10.3 How to confirm a new uploaded analysis_id has entered the system

When the local side uploads a new payload, record the expected `analysis_id` and then verify three places.

1. `recent` API:

```bash
curl -s "http://127.0.0.1:8011/api/recent-interaction-results?limit=10&classroom_id=classroom_101"
```

Check that the expected `analysis_id` appears in the JSON response and that its `source_kind=raw`.

2. raw file storage:

```bash
find /root/video_project_src/cloud_backend/data/raw -maxdepth 2 -type f | sort | tail -n 10
```

Check that a matching file such as:

```text
/root/video_project_src/cloud_backend/data/raw/YYYY-MM-DD/<analysis_id>.json
```

exists on disk.

3. dashboard:

```bash
curl -s "http://127.0.0.1:8011/dashboard?classroom_id=classroom_101&limit=10"
```

Check that the HTML contains the same `analysis_id` and still includes the `raw` source badge in the recent table.

### 10.4 How to check raw write and SQLite indexing stay aligned

Minimal alignment check:

1. raw file exists on disk
2. `recent` returns the same `analysis_id`
3. `recent` returns `source_kind=raw`
4. dashboard includes the same `analysis_id`

Optional row-level SQLite check if `sqlite3` CLI is installed:

```bash
sqlite3 /root/video_project_src/cloud_backend/data/cloud_results.sqlite3 \
  "select analysis_id, classroom_id, source_kind, generated_at from classroom_results order by generated_at desc, created_at desc limit 10;"
```

If checking a specific upload:

```bash
sqlite3 /root/video_project_src/cloud_backend/data/cloud_results.sqlite3 \
  "select analysis_id, classroom_id, source_kind, generated_at from classroom_results where analysis_id = 'cls_20260417_101_001';"
```

Interpretation:

- raw file exists but SQLite row is missing:
  - write durability still succeeded
  - SQLite indexing may have failed
- SQLite row exists but raw file is missing:
  - this is unexpected and should be treated as an error
- dashboard shows sample while raw and SQLite both contain the new result:
  - inspect classroom filter and recent query behavior first

### 10.5 Minimal daily inspection

Recommended daily operator checklist:

1. confirm listener:

```bash
ss -lntp | grep 8011
```

2. confirm health:

```bash
curl -i http://127.0.0.1:8011/health
```

3. confirm recent real data path:

```bash
curl -s "http://127.0.0.1:8011/api/recent-interaction-results?limit=5"
```

Check for:

- `fallback_to_sample=false`
- latest `source_kind=raw`
- plausible latest `analysis_id`

4. confirm raw write floor has new files:

```bash
find /root/video_project_src/cloud_backend/data/raw -maxdepth 2 -type f | sort | tail -n 5
```

5. confirm SQLite file still exists and has non-zero size:

```bash
ls -lh /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
```

6. confirm dashboard still surfaces real recent rows:

```bash
curl -s "http://127.0.0.1:8011/dashboard?limit=5" | grep -E "Teacher Results Center|badge\">raw|cls_"
```

### 10.6 Minimal operator helper script

Current helper script in the repo:

```text
/root/video_project_src/scripts/check_cloud_runtime_observability.sh
```

Example usage:

```bash
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

With classroom filter:

```bash
cd /root/video_project_src
CLASSROOM_ID=classroom_101 LIMIT=10 bash scripts/check_cloud_runtime_observability.sh
```

To verify a specific expected upload:

```bash
cd /root/video_project_src
CLASSROOM_ID=classroom_101 EXPECT_ANALYSIS_ID=cls_20260417_101_001 bash scripts/check_cloud_runtime_observability.sh
```

The script does not mutate runtime state. It only:

- prints SQLite file status
- prints newest raw files
- prints the recent API summary
- checks dashboard HTML markers
- optionally queries SQLite rows when `sqlite3` is available

### 10.7 How to judge whether the system is operating normally

Treat the current runtime as healthy only when all of the following hold at the same time:

1. process and port:
   - `8011` is listening
   - the service responds to `/health` with HTTP `200`
2. recent query path:
   - `recent` responds successfully
   - `RECENT_FALLBACK_TO_SAMPLE=false`
   - newest rows use `source_kind=raw`
3. latest upload visibility:
   - the latest `analysis_id` appears in `recent`
   - the same `analysis_id` is present in raw storage
4. dashboard path:
   - dashboard HTML still contains `Teacher Results Center`
   - dashboard HTML still contains the latest `analysis_id`
   - dashboard HTML still contains the `raw` source badge
5. storage state:
   - SQLite file exists and has non-zero size
   - raw directory contains recent files under the current date path

Treat the system as degraded if any of the following occurs:

- `RECENT_FALLBACK_TO_SAMPLE=true`
- newest `source_kind=sample`
- dashboard no longer shows the same latest `analysis_id` as `recent`
- raw file exists but the expected upload never appears in `recent`
- SQLite file disappears or stays at zero bytes

Recommended quick judgement command:

```bash
cd /root/video_project_src
CLASSROOM_ID=classroom_101 LIMIT=5 bash scripts/check_cloud_runtime_observability.sh
```

When the script output shows all of the following, the runtime can be treated as operating normally:

- `RECENT_SUCCESS=True`
- `RECENT_FALLBACK_TO_SAMPLE=False`
- `RECENT_1_SOURCE_KIND=raw`
- `DASHBOARD_TITLE_FOUND=true`
- `DASHBOARD_RAW_BADGE_FOUND=true`
- `DASHBOARD_LATEST_ANALYSIS_ID_FOUND=true`

## 11. Common troubleshooting

### 11.1 Service started on the wrong port

Symptom:

- `uvicorn` is running but `8011` is not listening

Checks:

- confirm `.env.runtime` was loaded
- confirm startup command used `scripts/deploy_cloud_backend.sh` or explicit `--port 8011`
- confirm no older process is still bound to `8010`

### 11.2 Backend unexpectedly stays on file mode

Symptom:

- startup log shows `Cloud query repository backend=file`

Checks:

- verify `/root/video_project_src/cloud_backend/.env.runtime` exists
- verify `CLOUD_DB_BACKEND=sqlite`
- verify `CLOUD_DATABASE_URL` points to a writable path
- restart the process after correcting the env file

### 11.3 SQLite file is missing

Symptom:

- no `cloud_results.sqlite3` file after startup or upload

Checks:

- verify `CLOUD_DATABASE_URL`
- verify parent directory under `cloud_backend/data/` is writable
- check startup log for repository backend line
- check upload log for `SQLite indexing failed after raw persistence`

### 11.4 Raw file was not written

Symptom:

- upload returns error or no file appears under `data/raw`

Checks:

- verify `CLOUD_RAW_DIR`
- verify directory permissions
- verify JSON passed schema validation
- check the returned `saved_path` in the POST response

### 11.5 Dashboard still looks like sample fallback

Symptom:

- `/dashboard` loads, but recent/latest do not show the uploaded real `analysis_id`

Checks:

- verify `GET /api/recent-interaction-results` returns `source_kind=raw`
- verify the target `classroom_id` matches the uploaded record
- verify raw JSON exists under `data/raw`
- verify SQLite recent rows contain the same `analysis_id`

### 11.6 External browser cannot reach 8011

Symptom:

- `curl 127.0.0.1:8011` works on the server, but browser access from outside fails

Checks:

- Alibaba Cloud security group has `8011/tcp` open
- server firewall (`ufw` or `iptables`) allows `8011/tcp`
- service is bound to `0.0.0.0`, not only `127.0.0.1`

## 12. SSHFS execution boundary

Under the current SSHFS workflow:

- code, docs, example env files, and helper scripts can be prepared from the mounted workspace
- actual service start, port check, curl verification, firewall check, and process-manager installation must be executed by the operator on the Linux server

Do not record those server-side actions as completed unless the operator runs them and returns the output.

## 13. Steady-State Operating Mode Choice

This section turns the current runtime from "works" into a documented long-term operating choice.

Current verified baseline:

- the service has been verified in foreground/manual-start mode
- the verified runtime shape is:
  - port `8011`
  - backend `sqlite`
  - raw fallback enabled
- a compatible systemd unit example already exists in:

```text
/root/video_project_src/cloud_backend/classroom-cloud-backend.service.example
```

No systemd installation or enablement is claimed here unless the operator executes those steps on the Linux server.

### 13.1 Foreground runtime: strengths and weaknesses

Foreground runtime means starting the service directly from the shell, for example:

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

Strengths:

- simplest path to start and verify
- matches the already validated baseline
- easy to inspect logs directly in the current terminal
- lowest change risk while the runtime is still being stabilized

Weaknesses:

- tied to a shell session unless the operator adds `tmux`, `screen`, or similar tools
- restart after reboot is manual
- restart after code or env changes is manual
- easier to lose process ownership or forget which terminal is authoritative
- weaker handoff story for long-term steady-state operation

### 13.2 systemd runtime: strengths and weaknesses

systemd runtime means the service is started and supervised by a Linux unit file based on the aligned example:

```text
/root/video_project_src/cloud_backend/classroom-cloud-backend.service.example
```

Strengths:

- automatic restart on abnormal exit
- explicit working directory and environment file
- better fit for long-term server operation
- standard service lifecycle commands for operator handoff
- easier to standardize restart and post-change procedure

Weaknesses:

- requires explicit operator installation steps on the Linux server
- adds one more layer to debug when the env file or unit path is wrong
- must be switched carefully so it does not conflict with a still-running foreground process
- should not be claimed as active until the operator runs `daemon-reload`, starts the service, and verifies status

### 13.3 Recommended steady-state choice

Current recommendation:

- short-term validated mode:
  - foreground/manual-start is accepted as the currently verified runtime baseline
- recommended steady-state mode:
  - `systemd`

Reasoning:

- the service is already stable enough to define explicit startup paths
- the project now has a verified runtime baseline, observability baseline, and aligned `.service.example`
- long-running automatic upload scenarios benefit from supervised restart and clearer operator ownership

Practical rule:

- if the operator is still making frequent runtime edits in the same session, keep foreground temporarily
- once the operator wants a formal long-term mode, move to `systemd`

### 13.4 If foreground continues: minimum maintenance pattern

If the operator keeps foreground mode for now, use this minimum pattern:

1. start only from the formal helper script:

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

2. keep the service in a dedicated terminal or `tmux`/`screen` session
3. after startup, verify:

```bash
ss -lntp | grep 8011
curl -i http://127.0.0.1:8011/health
```

4. run the observability script after restart or upload changes:

```bash
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

5. record the current choice in the steady-state template before handoff

Foreground should be treated as acceptable but temporary, not the preferred final host-management mode.

### 13.5 If switching to systemd: required prechecks

Before switching to systemd, the operator should verify all of the following on the Linux server:

1. the service works correctly in foreground mode on `8011`
2. the current env file is correct:

```text
/root/video_project_src/cloud_backend/.env.runtime
```

3. the current service example still matches intended paths:

```text
/root/video_project_src/cloud_backend/classroom-cloud-backend.service.example
```

4. no conflicting foreground process should remain bound to `8011` when the systemd service is started
5. the latest observability baseline is green:
   - `RECENT_FALLBACK_TO_SAMPLE=False`
   - latest `source_kind=raw`
   - dashboard markers present

### 13.6 If switching to systemd: operator steps to execute

These are operator actions only. They are not claimed as executed in this runbook.

Typical systemd adoption flow:

```bash
cp /root/video_project_src/cloud_backend/classroom-cloud-backend.service.example /etc/systemd/system/classroom-cloud-backend.service
systemctl daemon-reload
systemctl enable classroom-cloud-backend.service
systemctl start classroom-cloud-backend.service
systemctl status classroom-cloud-backend.service
journalctl -u classroom-cloud-backend.service -n 100 --no-pager
```

After that, re-verify:

```bash
ss -lntp | grep 8011
curl -i http://127.0.0.1:8011/health
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

### 13.7 Formal stop / restart / restart-after-change guidance

If the service remains in foreground mode:

- stop:
  - use `Ctrl+C` in the authoritative runtime terminal
- restart:
  - stop the old foreground process first
  - then rerun:

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

- restart after config or code change:
  - stop the old foreground process
  - confirm the updated files are present
  - rerun `bash scripts/deploy_cloud_backend.sh`
  - rerun `bash scripts/check_cloud_runtime_observability.sh`

If the service is moved to systemd:

- stop:

```bash
systemctl stop classroom-cloud-backend.service
```

- restart:

```bash
systemctl restart classroom-cloud-backend.service
```

- restart after config or code change:

```bash
systemctl restart classroom-cloud-backend.service
systemctl status classroom-cloud-backend.service
journalctl -u classroom-cloud-backend.service -n 100 --no-pager
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

If the unit file itself changed:

```bash
systemctl daemon-reload
systemctl restart classroom-cloud-backend.service
```

### 13.8 Decision rule for operator handoff

Use foreground as the current validated baseline only when:

- the operator still wants interactive terminal control
- the service is being changed frequently
- long-term auto-restart is not yet a hard requirement

Choose systemd as the formal steady-state mode when:

- the operator wants a long-running production-like mode
- reboots or terminal closure should not stop the service
- service ownership needs to be handed off cleanly
- continuous uploads are expected to run for extended periods
