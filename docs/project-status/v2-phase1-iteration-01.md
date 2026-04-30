# V2 Phase 1 Iteration 01

## 1. Scope

This iteration implements the V2 Phase 1 server-side additions defined by:

- `docs/specs/v2-phase1-sdd.md`
- `docs/tasks/v2-phase1-sdd.md`

Note:

- `docs/specs/v2-phase1-sdd.md` is now present and non-empty.
- The file content is currently mojibake in this SSHFS view, but the required V2 Phase 1 items are still identifiable.
- This follow-up alignment added the missing spec items: `GET /api/auth/me`, `GET /api/teacher/sessions/{analysis_id}`, `POSTGRES_URL` alias support, `JWT_SECRET` alias support, and `sessions.raw_json_path`.

## 2. Modified Files

Cloud backend:

- `cloud_backend/repository_interface.py`
- `cloud_backend/storage.py`
- `cloud_backend/postgres_repository.py`
- `cloud_backend/security.py`
- `cloud_backend/auth.py`
- `cloud_backend/config.py`
- `cloud_backend/main.py`
- `cloud_backend/requirements.txt`
- `cloud_backend/.env.runtime.example`

Scripts:

- `scripts/setup_postgres_schema.sh`
- `scripts/validate_postgres.sh`
- `scripts/validate_auth.sh`
- `scripts/validate_teacher_api.sh`

Project status:

- `docs/project-status/v2-phase1-iteration-01.md`

## 3. Baseline V1 Modules Preserved

The following baseline surfaces were not removed or renamed:

- `POST /api/interaction-results`
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /dashboard`
- `cloud_backend/dashboard_v11.py`
- raw JSON persistence through `FileResultRepository`
- SQLite query repository through `SQLiteResultRepository`
- file/sample fallback behavior

The upload path still writes raw JSON first:

```text
raw_repository.save(payload_dict_for_storage)
```

Then it indexes into the selected query repository only after raw persistence succeeds.

## 4. PostgreSQL Additions

Added:

- `cloud_backend/postgres_repository.py`

Implemented repository methods:

- `save_result`
- `get_recent`
- `get_latest`
- `get_teacher_sessions`

Compatibility methods for the existing repository contract:

- `save`
- `latest_result`
- `recent_results`
- `detail_result`

Selection rule:

- `CLOUD_DB_BACKEND=sqlite` keeps using SQLite
- `CLOUD_DB_BACKEND=postgres` uses `PostgreSQLResultRepository`
- any other value falls back to file repository

## 5. Repository Interface Extension

Updated:

- `cloud_backend/repository_interface.py`

Added:

```python
get_teacher_sessions(user_id: int) -> list[dict[str, Any]]
```

File and SQLite repositories currently return an empty list for this method because teacher ownership requires the PostgreSQL user/classroom tables.

## 6. Auth and API Additions

Added:

- `cloud_backend/security.py`
- `cloud_backend/auth.py`

Implemented:

- bcrypt password hashing
- JWT access token creation and validation
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/admin/users`
- `GET /api/admin/users`
- `GET /api/teacher/sessions`
- `GET /api/teacher/sessions/{analysis_id}`
- `GET /api/teacher/trends?limit=5`

Current behavior:

- auth/admin/teacher APIs require a PostgreSQL `CLOUD_DATABASE_URL`
- in SQLite-only runtime, these APIs return service unavailable instead of changing baseline SQLite behavior
- teacher APIs read teacher-visible classroom data through the selected repository

## 7. PostgreSQL Schema Script

Added:

- `scripts/setup_postgres_schema.sh`

Tables included:

- `users`
- `classrooms`
- `sessions`
- `analysis_results`

The `sessions` table includes `raw_json_path` so PostgreSQL indexing can point back to the raw JSON floor.

The script can also seed or refresh an admin user through:

```bash
CLOUD_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/classroom_cloud \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin-change-me \
bash scripts/setup_postgres_schema.sh
```

## 8. Validation Scripts

Added:

- `scripts/validate_postgres.sh`
- `scripts/validate_auth.sh`
- `scripts/validate_teacher_api.sh`

These scripts are operator-executed only. They were not run from SSHFS.

### 8.1 PostgreSQL schema validation

Command:

```bash
cd /root/video_project_src
CLOUD_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/classroom_cloud \
bash scripts/validate_postgres.sh
```

Expected output:

- four expected table names appear:
  - `analysis_results`
  - `classrooms`
  - `sessions`
  - `users`
- analysis result query returns rows or an empty result set
- `/health` returns HTTP `200`

### 8.2 Auth validation

Command:

```bash
cd /root/video_project_src
API_BASE_URL=http://127.0.0.1:8011 \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin-change-me \
TEACHER_USERNAME=teacher_101 \
TEACHER_PASSWORD=teacher-change-me \
CLASSROOM_ID=classroom_101 \
bash scripts/validate_auth.sh
```

Expected output:

- admin login succeeds
- an admin bearer token is acquired
- teacher user create/update returns JSON
- user list returns JSON containing users

### 8.3 Teacher API validation

Command:

```bash
cd /root/video_project_src
API_BASE_URL=http://127.0.0.1:8011 \
TEACHER_USERNAME=teacher_101 \
TEACHER_PASSWORD=teacher-change-me \
bash scripts/validate_teacher_api.sh
```

Expected output:

- teacher login succeeds
- `/api/teacher/sessions` returns HTTP `200`
- `/api/teacher/trends?limit=5` returns HTTP `200`
- returned lists may be empty if no classroom/session rows are linked yet

## 9. Static Validation Completed

Static compile check was run with Python bytecode cache redirected away from the SSHFS `__pycache__` path:

```powershell
$env:PYTHONPYCACHEPREFIX="$env:TEMP\codex_pycache"
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/security.py cloud_backend/auth.py cloud_backend/main.py
```

Result:

- passed

Initial compile attempt without cache redirection failed with:

```text
[WinError 5] Access denied: cloud_backend\__pycache__
```

That was a cache write issue, not a syntax error.

## 10. Operator-Only Steps Not Executed

The following were not executed in this SSHFS session:

- PostgreSQL database creation
- `scripts/setup_postgres_schema.sh`
- `scripts/validate_postgres.sh`
- `scripts/validate_auth.sh`
- `scripts/validate_teacher_api.sh`
- service restart in PostgreSQL mode
- real upload validation under `CLOUD_DB_BACKEND=postgres`

## 11. Current Risk Points

- `docs/specs/v2-phase1-sdd.md` is present but appears mojibake in the current SSHFS view, so future edits should preserve readable encoding.
- PostgreSQL mode requires the operator to set `CLOUD_DB_BACKEND=postgres` and a PostgreSQL `CLOUD_DATABASE_URL` or `POSTGRES_URL`.
- Auth APIs depend on the PostgreSQL schema being initialized first.
- Existing SQLite mode should continue to run, but full runtime verification still needs operator execution after dependency installation.
- `bcrypt` and `PyJWT` were added to `requirements.txt`; the server environment must reinstall requirements before auth routes can run.
- Teacher visibility depends on `classrooms.teacher_user_id` mappings.

## 13. Deployment Dependency Adjustment

During operator deployment on 2026-04-28, the configured pip mirror resolved PyJWT only up to `2.9.0` and failed to install `PyJWT==2.10.1`.

Adjustment made:

- `cloud_backend/requirements.txt` now pins `PyJWT==2.9.0`

Reason:

- `cloud_backend/security.py` only uses stable PyJWT 2.x APIs: `jwt.encode`, `jwt.decode`, and `jwt.PyJWTError`.
- `PyJWT==2.9.0` is compatible with the current V2 Phase 1 auth implementation.
- No API route, schema, dashboard, upload path, raw fallback, SQLite fallback, or PostgreSQL repository logic was changed.

## 14. Python 3.8 Runtime Compatibility Adjustment

During operator startup on Python 3.8, FastAPI/Pydantic failed while evaluating route annotations that used Python 3.9+ built-in generic syntax such as:

```text
dict[str, Any]
```

Adjustment made:

- `cloud_backend/auth.py` now uses `typing.Dict` for FastAPI route/dependency annotations.
- `cloud_backend/security.py`, `cloud_backend/repository_interface.py`, and `cloud_backend/postgres_repository.py` were aligned to `typing.Dict`, `typing.List`, and `typing.Tuple` for Python 3.8 compatibility.
- `cloud_backend/auth.py` replaced `str.removeprefix`, which is unavailable on Python 3.8, with equivalent slicing.

Validation:

```powershell
$env:PYTHONPYCACHEPREFIX="$env:TEMP\codex_pycache"
python -m py_compile cloud_backend/repository_interface.py cloud_backend/postgres_repository.py cloud_backend/security.py cloud_backend/auth.py cloud_backend/main.py
```

Result:

- passed

Scope control:

- No existing upload interface was changed.
- No dashboard structure was changed.
- No raw JSON persistence or SQLite fallback behavior was removed.
- No PostgreSQL schema or route naming was changed.

## 15. Operator Validation Results

Operator validation was run on the cloud server on 2026-04-28 with:

```bash
export CLOUD_DATABASE_URL='postgresql://classroom_user:classroom_pass@127.0.0.1:5432/classroom_cloud'
export API_BASE_URL='http://127.0.0.1:8011'
export ADMIN_USERNAME='admin'
export ADMIN_PASSWORD='admin-change-me'
```

### 15.1 PostgreSQL Validation

Command:

```bash
bash scripts/validate_postgres.sh
```

Observed result:

```text
[step] checking PostgreSQL tables
    table_name
------------------
 analysis_results
 classrooms
 sessions
 users
(4 rows)

[step] checking analysis_results rows
 analysis_id | classroom_id | source_kind | generated_at
-------------+--------------+-------------+--------------
(0 rows)

[step] checking cloud health endpoint
HTTP/1.1 200 OK
{"status":"ok"}
[done] PostgreSQL validation commands completed
```

Status:

- passed
- `analysis_results` is currently empty because no result has been uploaded while running in PostgreSQL mode yet.

### 15.2 Auth Validation

Command:

```bash
bash scripts/validate_auth.sh
```

Observed result:

```text
[step] admin login
[info] admin token acquired
[step] current user
{"success":true,"user":{"id":1,"username":"admin","role":"admin"}}
[step] create teacher user
{"success":true,"user":{"id":2,"username":"teacher_101","role":"teacher","is_active":true,"created_at":"2026-04-28T09:59:47.028226+08:00"}}
[step] list users
{"success":true,"users":[{"id":1,"username":"admin","role":"admin","is_active":true,"created_at":"2026-04-28T09:20:51.469313+08:00","classrooms":[]},{"id":2,"username":"teacher_101","role":"teacher","is_active":true,"created_at":"2026-04-28T09:59:47.028226+08:00","classrooms":["classroom_101"]}]}
[done] auth validation completed
```

Status:

- passed
- admin login works
- `/api/auth/me` works
- teacher user `teacher_101` is created/updated
- classroom ownership mapping for `classroom_101` exists

### 15.3 Teacher API Validation

Command:

```bash
bash scripts/validate_teacher_api.sh
```

Observed result:

```text
[step] teacher login
[step] teacher sessions
{"success":true,"sessions":[]}
[info] no teacher sessions available; skipping session detail check

[step] teacher trends
HTTP/1.1 200 OK
{"success":true,"limit":5,"trends":[]}
[done] teacher API validation completed
```

Status:

- passed
- teacher login works
- `/api/teacher/sessions` returns `200` with an empty list
- `/api/teacher/trends?limit=5` returns `200` with an empty list
- empty teacher data is expected before a PostgreSQL-mode upload is indexed into `analysis_results`

## 16. Current Phase 1 Validation State

Completed:

- PostgreSQL schema exists.
- PostgreSQL connection works through the application validation scripts.
- Cloud service health endpoint returns `200`.
- Auth API returns a JWT token for admin login.
- Admin API can create/list teacher users.
- Teacher API returns valid empty responses.

Still pending:

- none for V2 Phase 1 implementation and validation baseline.

## 17. PostgreSQL-Mode Upload and Teacher API Validation

Operator uploaded a real V1.1 classroom result while the service was running with `CLOUD_DB_BACKEND=postgres`.

Upload command:

```bash
bash scripts/upload_real_result.sh
```

Observed result:

```text
HTTP_STATUS=200
RESPONSE_BODY=
{"success":true,"message":"课堂交互结果接收成功","request_id":"e856c77a-0892-4bce-b1f0-9e0b2a4b8ddf","saved_path":"/root/video_project_src/cloud_backend/data/raw/2026-04-28/cls_20260417_101_001.json"}
SUCCESS
```

PostgreSQL validation after upload:

```text
     analysis_id      | classroom_id  | source_kind |      generated_at
----------------------+---------------+-------------+------------------------
 cls_20260417_101_001 | classroom_101 | raw         | 2026-04-19 21:05:02+08
(1 row)
```

Teacher API validation after upload:

```text
[step] teacher sessions
{"success":true,"sessions":[{"analysis_id":"cls_20260417_101_001","classroom_id":"classroom_101","video_id":"video_20260417_001","recorded_at":"2026-04-17T17:00:00+08:00","generated_at":"2026-04-19T21:05:02+08:00","duration_seconds":528.0,"raw_json_path":"/root/video_project_src/cloud_backend/data/raw/2026-04-28/cls_20260417_101_001.json","source_kind":"raw","source_path":"/root/video_project_src/cloud_backend/data/raw/2026-04-28/cls_20260417_101_001.json","feedback_score":39.55,"attention_score":73.0,"response_score":16.36}]}
```

Teacher detail endpoint:

```text
HTTP/1.1 200 OK
```

Teacher trends endpoint:

```text
HTTP/1.1 200 OK
{"success":true,"limit":5,"trends":[{"analysis_id":"cls_20260417_101_001","classroom_id":"classroom_101","generated_at":"2026-04-19T21:05:02+08:00","feedback_score":39.55,"attention_score":73.0,"response_score":16.36,"source_kind":"raw"}]}
```

Status:

- upload endpoint still returns `200`
- raw JSON still writes to `/root/video_project_src/cloud_backend/data/raw`
- PostgreSQL `analysis_results` receives the uploaded row
- teacher sessions now returns the uploaded `classroom_101` result
- teacher session detail returns the full stored payload
- teacher trends returns the uploaded result metrics

## 18. Recent and Dashboard Final Validation

Operator validated recent and dashboard after PostgreSQL-mode upload.

Recent command:

```bash
curl -i "http://127.0.0.1:8011/api/recent-interaction-results?limit=5&classroom_id=classroom_101"
```

Observed result:

```text
HTTP/1.1 200 OK
{"success":true,"limit":5,"classroom_id":"classroom_101","fallback_to_sample":false,"results":[{"source_kind":"raw","source_path":"/root/video_project_src/cloud_backend/data/raw/2026-04-28/cls_20260417_101_001.json","summary":{"analysis_id":"cls_20260417_101_001","classroom_id":"classroom_101","feedback_score":39.55,"attention_score":73.0,"response_score":16.36,"teacher_question_count":11,"response_success_rate":0.1818}}]}
```

Dashboard command:

```bash
curl -i "http://127.0.0.1:8011/dashboard?classroom_id=classroom_101&limit=5"
```

Observed result:

```text
HTTP/1.1 200 OK
<title>Cloud Classroom Results Center</title>
Analysis: cls_20260417_101_001
Classroom: classroom_101
Feedback Score: 39.55
Attention Score: 73.0
Response Score: 16.36
Teacher Question Count: 11.0
Response Success Rate: 0.18
Source: raw
```

Status:

- recent endpoint returns `200`
- recent endpoint returns `fallback_to_sample=false`
- recent endpoint includes `cls_20260417_101_001`
- dashboard returns `200`
- dashboard displays `cls_20260417_101_001`
- dashboard displays the real uploaded metrics and `raw` source badge

## 19. Final V2 Phase 1 Status

V2 Phase 1 implementation and validation baseline is complete.

Confirmed:

- Baseline `POST /api/interaction-results` remains unchanged and returns `200`.
- raw JSON write path remains active.
- SQLite/file fallback code remains present.
- PostgreSQL schema initializes successfully.
- PostgreSQL repository indexes uploaded V1.1 results.
- Auth login returns JWT tokens.
- Admin user management APIs work.
- Teacher sessions, detail, and trends APIs work with classroom ownership.
- Existing recent endpoint and dashboard remain accessible and show the uploaded real result.

Not included in this phase:

- PostgreSQL as the only backend.
- dashboard structure changes.
- trend/detail UI expansion.
- production systemd switchover.
- password/secret rotation policy beyond the current validation config.

## 12. Recommended Next Operator Sequence

1. Keep the current SQLite baseline running if production validation is in progress.
2. On a separate PostgreSQL-ready runtime, initialize schema:

```bash
cd /root/video_project_src
CLOUD_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/classroom_cloud \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin-change-me \
bash scripts/setup_postgres_schema.sh
```

3. Start the cloud backend with:

```bash
CLOUD_DB_BACKEND=postgres
CLOUD_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/classroom_cloud
```

4. Run:

```bash
bash scripts/validate_postgres.sh
bash scripts/validate_auth.sh
bash scripts/validate_teacher_api.sh
```
