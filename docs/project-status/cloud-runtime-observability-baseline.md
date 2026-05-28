# Cloud Runtime Observability Baseline

## Status

Verified from operator-provided Linux-server output on 2026-04-20.

Current result:

- the observability script completed successfully
- the service was reachable on `127.0.0.1:8011`
- `recent` reported real runtime data rather than sample fallback
- dashboard markers matched the latest real `analysis_id`
- SQLite file and raw files were both present

Baseline command used:

```bash
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

Under the current SSHFS workflow, the script output cannot be produced locally from the mounted workspace alone.

## 1. Script Output

Observed operator output:

```text
[info] API_BASE_URL=http://127.0.0.1:8011
[info] CLASSROOM_ID=<none>
[info] LIMIT=5
[info] EXPECT_ANALYSIS_ID=<none>
[info] SQLITE_PATH=/root/video_project_src/cloud_backend/data/cloud_results.sqlite3
[info] RAW_DIR=/root/video_project_src/cloud_backend/data/raw
[step] check sqlite file
-rw-r--r-- 1 root root 16384 Apr 20 20:25 /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
[step] list newest raw files
/root/video_project_src/cloud_backend/data/raw/2026-04-19/cls_20260417_101_001.json
/root/video_project_src/cloud_backend/data/raw/2026-04-20/classroom_20260417_001.json
/root/video_project_src/cloud_backend/data/raw/2026-04-20/cls_20260417_101_001.json
[step] query recent API
RECENT_SUCCESS=True
RECENT_CLASSROOM_ID=None
RECENT_LIMIT=5
RECENT_FALLBACK_TO_SAMPLE=False
RECENT_RESULT_COUNT=1
RECENT_1_ANALYSIS_ID=cls_20260417_101_001
RECENT_1_SOURCE_KIND=raw
RECENT_1_GENERATED_AT=2026-04-20T12:25:55Z
RECENT_1_SOURCE_PATH=/root/video_project_src/cloud_backend/data/raw/2026-04-20/cls_20260417_101_001.json
[step] query dashboard HTML
DASHBOARD_TITLE_FOUND=true
DASHBOARD_RAW_BADGE_FOUND=true
DASHBOARD_LATEST_ANALYSIS_ID_FOUND=true
DASHBOARD_LATEST_ANALYSIS_ID=cls_20260417_101_001
DASHBOARD_CLASSROOM_FILTER_FOUND=false
[step] optional sqlite row check
cls_20260417_101_001|classroom_101|raw|2026-04-20T12:25:55Z
```

Current interpretation:

- the script itself started correctly
- SQLite file detection worked
- raw file listing worked
- recent API check succeeded
- dashboard marker check succeeded
- optional SQLite row query succeeded

Operator note:

- the attempted `tee /root/video_project_src/` target was a directory, not a file
- correct usage is:

```bash
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh | tee /root/video_project_src/cloud_runtime_observability_baseline.out
```

## 2. Current Analysis ID List

Observed from the verified baseline run:

```text
RECENT_1_ANALYSIS_ID=cls_20260417_101_001
RECENT_1_SOURCE_KIND=raw
RECENT_1_GENERATED_AT=2026-04-20T12:25:55Z
RECENT_1_SOURCE_PATH=/root/video_project_src/cloud_backend/data/raw/2026-04-20/cls_20260417_101_001.json
```

Current interpretation:

- the latest visible result is `cls_20260417_101_001`
- the latest visible result came from `raw`
- the current baseline output contained one recent result

Expected source:

- `RECENT_<N>_ANALYSIS_ID=...`
- `RECENT_<N>_SOURCE_KIND=...`
- `RECENT_<N>_GENERATED_AT=...`

## 3. Raw File State

Observed from the verified baseline run:

```text
/root/video_project_src/cloud_backend/data/raw/2026-04-19/cls_20260417_101_001.json
/root/video_project_src/cloud_backend/data/raw/2026-04-20/classroom_20260417_001.json
/root/video_project_src/cloud_backend/data/raw/2026-04-20/cls_20260417_101_001.json
```

Current interpretation:

- raw files exist on disk
- the raw write floor is present even though the live API was unreachable during this run

Expected source:

- `[step] list newest raw files`
- file paths under `/root/video_project_src/cloud_backend/data/raw/`

## 4. SQLite State

Observed from the verified baseline run:

```text
-rw-r--r-- 1 root root 16384 Apr 20 20:25 /root/video_project_src/cloud_backend/data/cloud_results.sqlite3
cls_20260417_101_001|classroom_101|raw|2026-04-20T12:25:55Z
```

Current interpretation:

- the configured SQLite file exists
- the optional SQLite row query succeeded
- SQLite currently contains the same `analysis_id` seen by `recent`

Expected source:

- `[step] check sqlite file`
- optional SQLite row output if `sqlite3` is installed

## 5. Dashboard State

Observed from the verified baseline run:

```text
DASHBOARD_TITLE_FOUND=true
DASHBOARD_RAW_BADGE_FOUND=true
DASHBOARD_LATEST_ANALYSIS_ID_FOUND=true
DASHBOARD_LATEST_ANALYSIS_ID=cls_20260417_101_001
DASHBOARD_CLASSROOM_FILTER_FOUND=false
```

Current interpretation:

- dashboard responded with the expected title marker
- dashboard contained the `raw` badge
- dashboard contained the same latest `analysis_id` as `recent`
- this unfiltered baseline run did not assert a classroom-specific filter marker

Expected source:

- `DASHBOARD_TITLE_FOUND=...`
- `DASHBOARD_RAW_BADGE_FOUND=...`
- `DASHBOARD_LATEST_ANALYSIS_ID_FOUND=...`
- `DASHBOARD_LATEST_ANALYSIS_ID=...`
- `DASHBOARD_CLASSROOM_FILTER_FOUND=...`

## 6. Completion Rule

This baseline should be marked complete only after the operator output confirms:

- `RECENT_FALLBACK_TO_SAMPLE=False`
- newest `source_kind=raw`
- latest `analysis_id` visible in recent output
- latest `analysis_id` visible in dashboard markers
- SQLite file exists
- raw files exist

Current completion result:

- completion rule satisfied
- baseline verified

## 7. Next Operator Step

1. if a classroom-specific baseline is needed, rerun:

```bash
cd /root/video_project_src
CLASSROOM_ID=classroom_101 bash scripts/check_cloud_runtime_observability.sh | tee /root/video_project_src/cloud_runtime_observability_baseline.out
```

2. keep the successful output file under a real filename, not the directory path itself
