# V2 Phase 2.8.1 Spec: Cloud Scripted Verification Support

## 1. Purpose

Phase 2.8.1 does not add new cloud product scope. It ensures the cloud can display and validate Phase 2.8.1 metadata uploaded by the local analyzer.

Cloud remains responsible for:

- accepting `/api/interaction-results`
- serving `/api/admin/ingestion`
- serving `/admin/ingestion`
- serving `/dashboard?result_id=...`

## 2. Non-Goals

Do not implement:

- new database tables
- new upload API
- video asset table
- video transcoding
- permission/login system
- device heartbeat
- daemon

## 3. Metadata Compatibility

Uploaded result JSON may now include:

```text
video.standardized_video_path
video.browser_compatible
video.transcode_status
video.transcode_error
```

Cloud should tolerate these fields and display or summarize them when useful.

Older payloads without these fields remain valid.

## 4. Existing API

Keep:

```text
GET /api/admin/ingestion
GET /admin/ingestion
GET /dashboard?result_id=<result_id>
```

No new endpoint is required.

## 5. Verification

Existing script:

```text
scripts/validate_phase2_8_ingestion_status.sh
```

Should support:

```bash
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="<result_id>" CLASSROOM_ID="classroom_101" bash scripts/validate_phase2_8_ingestion_status.sh
```

Local analyzer may also perform HTTP checks directly against public cloud URL.

