# Cloud SQLite Repository Iteration 01

## 1. Goal

Introduce a repository abstraction and a minimal SQLite-backed query/index implementation without changing the current API routes or dashboard entry.

This iteration was limited to:

- repository abstraction
- SQLite-backed latest/recent query path
- raw JSON write retention
- validation and documentation

## 2. Modified Files

- `cloud_backend/repository_interface.py`
- `cloud_backend/storage.py`
- `cloud_backend/main.py`
- `cloud_backend/dashboard_v11.py`
- `docs/specs/cloud-storage-repository-v1.md`
- `docs/project-status/cloud-sqlite-repository-iteration-01.md`

## 3. Spec Document

Spec path:

- [cloud-storage-repository-v1.md](x:\video_project_src\docs\specs\cloud-storage-repository-v1.md)

## 4. Repository Abstraction

This iteration adds:

- `ResultRepository` protocol in [repository_interface.py](x:\video_project_src\cloud_backend\repository_interface.py)

Current repository responsibilities:

- `save`
- `latest_result`
- `recent_results`
- `detail_result`

Current concrete implementations:

- `FileResultRepository`
  - raw JSON persistence
  - file-based fallback queries
- `SQLiteResultRepository`
  - normalized summary row storage
  - SQLite-backed latest/recent queries
  - fallback to file queries when SQLite is empty or unavailable

Repository selection now happens through:

- `build_query_repository(settings, raw_repository)` in [storage.py](x:\video_project_src\cloud_backend\storage.py)

## 5. SQLite Integration

SQLite integration is controlled by:

- `CLOUD_DB_BACKEND=sqlite`
- optional `CLOUD_DATABASE_URL`

Behavior in this iteration:

1. API handler validates V1.1 payload
2. raw JSON is always written first by `FileResultRepository`
3. when `db_backend=sqlite`, the same payload is indexed into SQLite
4. latest/recent queries use the selected repository

Current SQLite table:

- `classroom_results`

Stored row shape includes:

- `analysis_id`
- `classroom_id`
- `video_id`
- `schema_version`
- `source_kind`
- `source_path`
- `source_host`
- `recorded_at`
- `generated_at`
- `duration_seconds`
- `feedback_score`
- `attention_score`
- `response_score`
- `teacher_question_count`
- `avg_attention_ratio`
- `response_success_rate`
- `summary_text`
- `payload_json`
- `created_at`

## 6. Raw Safety Strategy

Raw file persistence remains in place.

Current rule:

- raw JSON is written before SQLite indexing

Current consequence:

- if SQLite indexing fails, raw persistence still succeeds
- the current API path is not forced to depend on SQLite for write durability

Raw safety is therefore retained.

## 7. Validation Results

Validation was executed with:

- `CLOUD_DB_BACKEND=sqlite`
- `CLOUD_DATA_DIR=cloud_backend/data/sqlite_validation_runtime`
- `CLOUD_DATABASE_URL=cloud_backend/data/sqlite_validation_runtime/cloud_results.sqlite3`
- payload source: `cls_20260417_101_001.json`

Observed results:

- repository backend: `sqlite`
- SQLite file created: `cloud_backend/data/sqlite_validation_runtime/cloud_results.sqlite3`
- SQLite row inserted:
  - `('cls_20260417_101_001', 'classroom_101', 'raw')`
- POST validation write returned `200`
- raw JSON persisted at:
  - `cloud_backend/data/sqlite_validation_runtime/raw/2026-04-20/cls_20260417_101_001.json`
- recent query returned `200`
- recent result `source_kind` was `raw`
- recent result `analysis_id` was `cls_20260417_101_001`
- dashboard returned `200`
- dashboard still rendered:
  - `Teacher Results Center`
  - `Response Score`
  - the uploaded `analysis_id`

Current conclusion:

- SQLite creation validation: passed
- SQLite write validation: passed
- recent from SQLite path: passed
- dashboard compatibility after SQLite integration: passed

## 8. Current Query Source

In the validation run, `recent` was served from `SQLiteResultRepository`.

Basis:

- runtime `repository.backend_name` was `sqlite`
- recent query returned the uploaded record with `source_kind=raw`
- the SQLite row for the same `analysis_id` existed

## 9. Unfinished Items

- no public detail route yet, although repository-level `detail_result` exists
- no trend aggregation yet
- no PostgreSQL path
- no formal migration from existing raw history into SQLite
- no runtime-facing documentation update yet for choosing `file` vs `sqlite` backend in deployment

## 10. Next-Step Suggestions

1. Add a minimal deployment-facing environment example for `CLOUD_DB_BACKEND=sqlite` and `CLOUD_DATABASE_URL`.
2. Add a public detail endpoint only if the team is ready to make `analysis_id` a formal lookup contract.
3. Decide whether real deployed recent/latest should switch to SQLite now, or stay file-backed until more raw history is indexed.
