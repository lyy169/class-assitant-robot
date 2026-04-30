# V2 Phase 2.8.1 Runbook: Three-Side Scripted Validation

## 1. Purpose

Validate the scripted handoff chain:

```text
Raspberry Pi script
  -> handoff JSON
  -> local consume/upload script
  -> cloud ingestion/dashboard validation
```

## 2. Raspberry Pi Command

Run on Raspberry Pi:

```bash
cd <raspberry-pi-project>
bash scripts/phase2_8_1_capture_prepare.sh --classroom-id classroom_101 --duration 30
```

Expected:

```text
PHASE281_PI_OK=true
PHASE281_HANDOFF_FILE_EXISTS=true
PHASE281_STANDARDIZED_VIDEO_PATH=...
PI_CAPTURE_METADATA_VALID=true
```

## 3. Local Analyzer Command

Run on local analyzer:

```powershell
python scripts/phase2_8_1_consume_latest_upload.py `
  --handoff-file "Y:\lyy\PI-Assistant-master1\PI-Assistant-master\phase2_8_1_latest_session.json" `
  --pi-sshfs-root "Y:\lyy\PI-Assistant-master1\PI-Assistant-master" `
  --api-base-url "http://8.148.205.228:8011"
```

Expected:

```text
PHASE281_LOCAL_OK=true
PHASE281_RESULT_ID=...
PHASE281_UPLOAD_OK=true
PHASE281_CLOUD_INGESTION_API_OK=true
PHASE281_CLOUD_DASHBOARD_OK=true
```

## 4. Optional Cloud Server Command

If server-side validation is needed, run on cloud server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="<result_id>" CLASSROOM_ID="classroom_101" bash scripts/validate_phase2_8_ingestion_status.sh
```

Expected cloud markers:

```text
PHASE28_ADMIN_INGESTION_PAGE_OK=true
PHASE28_ADMIN_INGESTION_API_OK=true
PHASE28_ADMIN_INGESTION_KEYS_OK=true
PHASE281_VIDEO_STANDARD_METADATA_KEYS_OK=true
PHASE27_ADMIN_REGRESSION_OK=true
PHASE26_TEACHER_REGRESSION_OK=true
PHASE25_DASHBOARD_REGRESSION_OK=true
PHASE12_API_REGRESSION_OK=true
```

## 5. Browser Check

Open:

```text
http://8.148.205.228:8011/admin/ingestion
```

Confirm:

- uploaded result appears
- device/classroom metadata is visible
- video metadata is reasonable
- standardized video metadata is visible when uploaded:
- `standardized_video_path` presence
- `browser_compatible`
- `transcode_status`
- `transcode_error` if present
- dashboard link opens

## 6. Pass Criteria

Pass when:

- Raspberry Pi script produces handoff and standardized video
- local script consumes handoff and uploads result
- cloud ingestion API/page can see result
- dashboard opens for result
