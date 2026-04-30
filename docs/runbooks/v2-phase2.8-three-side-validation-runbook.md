# V2 Phase 2.8 Three-Side Validation Runbook

## Purpose

Validate the metadata flow across:

```text
Raspberry Pi capture side
  -> local analyzer side
  -> cloud backend
```

## 1. Raspberry Pi Side Validation

Important:

- The Raspberry Pi project may be connected through SSHFS.
- Use SSHFS for editing files and collecting logs only.
- Do not treat SSHFS as proof that camera, codec, or runtime services work on the device.
- Hardware/runtime validation must be run on the Raspberry Pi itself by the operator.

Expected file:

```text
capture_metadata.json
```

Recommended script:

```bash
cd <raspberry-pi-project>
bash scripts/validate_capture_metadata.sh
```

If the script is not available yet, validate manually on the Raspberry Pi:

```bash
python -m json.tool capture_metadata.json >/dev/null
```

Required keys:

- `capture.device_id`
- `capture.classroom_id`
- `capture.captured_at`

Expected markers:

```text
PI_CAPTURE_METADATA_VALID=true
PI_CAPTURE_DEVICE_ID_PRESENT=true
PI_CAPTURE_CLASSROOM_ID_PRESENT=true
PI_CAPTURE_TIME_PRESENT=true
PI_CAPTURE_VIDEO_PATH_PRESENT=true/false
PI_CAPTURE_KEYFRAME_DIR_PRESENT=true/false
```

## 2. Local Analyzer Side Validation

Expected final JSON:

```text
result.json
```

Validate JSON:

```bash
python -m json.tool result.json >/dev/null
```

Check metadata:

```bash
python - <<'PY'
import json
payload = json.load(open("result.json", encoding="utf-8"))
for key in ["source", "capture", "video", "upload"]:
    assert key in payload, key
print("LOCAL_SESSION_JSON_VALID=true")
print("LOCAL_SOURCE_PRESENT=true")
print("LOCAL_CAPTURE_PRESENT=true")
print("LOCAL_VIDEO_PRESENT=true")
print("LOCAL_UPLOAD_PRESENT=true")
print("LOCAL_TEACHER_QUESTION_EVENTS_PRESERVED=" + str(bool((payload.get("teacher") or {}).get("question_events"))).lower())
PY
```

Video capability audit should output:

```text
LOCAL_VIDEO_TRANSCODE_CAPABILITY=present/absent/unknown
LOCAL_VIDEO_OUTPUT_BROWSER_COMPATIBLE=true/false/unknown
```

## 3. Upload To Cloud

```bash
curl -i -XPOST "http://<cloud-host>:8011/api/interaction-results" \
  -H "Content-Type: application/json" \
  -d @result.json
```

Expected:

- HTTP `200`
- response `success=true`
- saved raw path returned

## 4. Cloud Runtime Validation

Start service:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Run:

```bash
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" CLASSROOM_ID="classroom_101" bash scripts/validate_phase2_8_ingestion_status.sh
```

Expected cloud markers:

```text
PHASE28_ADMIN_INGESTION_PAGE_OK=true
PHASE28_ADMIN_INGESTION_API_OK=true
PHASE28_ADMIN_INGESTION_KEYS_OK=true
PHASE27_ADMIN_REGRESSION_OK=true
PHASE26_TEACHER_REGRESSION_OK=true
PHASE25_DASHBOARD_REGRESSION_OK=true
PHASE12_API_REGRESSION_OK=true
```

Manual API:

```bash
curl -s "http://127.0.0.1:8011/api/admin/ingestion" | tee /tmp/phase28-ingestion.json
```

Expected keys:

- success
- filters
- overview
- pipeline
- devices
- recent_ingestions
- video_summary
- validation_hints

## 5. Browser Validation

Open:

```text
http://<server-ip>:8011/admin/ingestion
```

Expected:

- Admin Console navigation
- Capture -> Local Analysis -> Cloud Storage -> Teacher Feedback pipeline
- metric cards
- filters
- device/analyzer list
- recent ingestion records
- video readiness summary
- validation/data-quality hints

## 6. Regression

Validate:

```bash
curl -i "http://127.0.0.1:8011/admin"
curl -i "http://127.0.0.1:8011/teacher"
curl -i "http://127.0.0.1:8011/dashboard?result_id=cls_20260417_101_001"
curl -i "http://127.0.0.1:8011/api/latest-interaction-result"
curl -i "http://127.0.0.1:8011/api/recent-interaction-results?limit=5"
```

Expected:

- all return `200`

## 7. Final Report

Report:

- Raspberry Pi metadata result
- local analyzer metadata result
- local video capability audit result
- cloud upload result
- cloud ingestion API result
- cloud ingestion page result
- regression result
- unresolved risks
