# V2 Phase 2.8 Spec: Three-Side Ingestion Status

## 1. Background

Phase 2.5 completed single classroom analysis detail.
Phase 2.6 completed the teacher home and classroom records center.
Phase 2.7 completed the admin console and platform overview.

Phase 2.8 focuses on the credibility of the full three-side data flow:

```text
Raspberry Pi capture side
  -> local analyzer side
  -> cloud backend
  -> admin/teacher dashboard
```

The purpose is to make uploaded classroom results traceable to capture devices, local analyzers, source files, video metadata, and cloud receipt status.

## 2. Stage Goal

Phase 2.8 builds:

- a three-side metadata contract
- Raspberry Pi capture-side metadata requirements
- local analyzer session/upload metadata requirements
- cloud ingestion status API
- `/admin/ingestion` admin page
- three-side validation runbook

The stage proves that classroom data is not static demo data, but part of a visible capture-analysis-upload-display chain.

## 3. Scope

In scope:

- metadata fields for `source`, `capture`, `video`, and `upload`
- optional preservation of `teacher.question_events` and `teacher.question_summary`
- cloud-side inference of device/source/video/ingestion status
- admin ingestion status page
- validation scripts and runbooks
- local-side video format capability audit

Out of scope:

- device CRUD
- true device heartbeat
- WebSocket online tracking
- video upload API
- upload-time video transcoding
- YOLO algorithm rewrite
- Raspberry Pi capture pipeline rewrite
- permission system
- new core database tables

## 4. Three-Side Responsibilities

### 4.1 Raspberry Pi Capture Side

Responsible for:

- recording classroom video/keyframes
- generating or passing capture metadata
- identifying device, classroom, and capture time

Not responsible for:

- cloud upload
- YOLO analysis
- final classroom analysis JSON
- cloud video transcoding

### 4.2 Local Analyzer Side

Responsible for:

- reading Raspberry Pi metadata
- running YOLO and classroom behavior analysis
- assembling the final classroom session JSON
- adding source/capture/video/upload metadata
- preserving teacher question events when available
- uploading JSON to `POST /api/interaction-results`
- auditing whether an existing video format standardization capability exists

### 4.3 Cloud Side

Responsible for:

- receiving existing classroom result JSON
- preserving raw JSON
- indexing PostgreSQL as before
- reading `payload_json` metadata
- deriving ingestion status
- rendering `/admin/ingestion`

## 5. System Flow

```text
Raspberry Pi captures classroom media
  -> writes capture metadata
  -> local analyzer reads media and metadata
  -> local analyzer runs YOLO/behavior analysis
  -> local analyzer builds classroom session JSON
  -> local analyzer uploads JSON to cloud
  -> cloud stores raw JSON
  -> cloud indexes PostgreSQL
  -> cloud derives ingestion status from payload_json
  -> admin reviews /admin/ingestion
  -> admin opens /dashboard?result_id=xxx for classroom detail
```

## 6. Metadata Contract

Phase 2.8 adds optional extra fields to the existing V1.1 classroom result payload.

Do not remove or rename existing fields.

Required existing blocks remain:

- `schema_version`
- `analysis_id`
- `classroom_id`
- `video_id`
- `source`
- `time`
- `summary`
- `teacher`
- `students`
- `timeline`

New/strengthened metadata blocks:

- `capture`
- `video`
- `upload`

Recommended shape:

```json
{
  "source": {
    "source_kind": "local_analyzer",
    "source_host": "local-pc-lab-01",
    "source_path": "/data/classroom_101/session_001/result.json"
  },
  "capture": {
    "device_id": "pi-classroom-101",
    "device_name": "Raspberry Pi - Classroom 101",
    "classroom_id": "classroom_101",
    "captured_at": "2026-04-29T09:00:00+08:00",
    "video_path": "/data/classroom_101/session_001/video.mp4",
    "keyframe_dir": "/data/classroom_101/session_001/keyframes"
  },
  "video": {
    "video_id": "video_20260429_101_001",
    "raw_video_path": "/data/classroom_101/session_001/video.mp4",
    "video_url": "",
    "duration_seconds": 600,
    "format": "mp4",
    "codec": "h264",
    "browser_compatible": true,
    "transcode_capability": "present"
  },
  "upload": {
    "uploaded_at": "2026-04-29T09:30:00+08:00",
    "target": "cloud_backend",
    "api": "/api/interaction-results",
    "client_version": "local-analyzer-v1"
  }
}
```

## 7. Teacher Question Future Hook

Teacher question guidance analysis is a future teaching-intelligence feature.

Phase 2.8 should preserve, but not deeply analyze, these optional fields:

```json
{
  "teacher": {
    "question_events": [],
    "question_summary": {
      "total_count": 0,
      "open_question_count": 0,
      "closed_question_count": 0,
      "response_count": 0,
      "response_rate": 0
    }
  }
}
```

Future phase may use this for teacher question guidance analysis.

## 8. Database Design

Phase 2.8 does not add core database tables or columns.

Use:

- `analysis_results`
- `sessions`
- `classrooms`
- `users`
- `analysis_results.payload_json`

Metadata lives in:

```text
raw JSON
analysis_results.payload_json
```

Device status is inferred from latest upload/receive time. It is not a true heartbeat status.

Future tables such as `devices`, `device_heartbeats`, `video_assets`, and `ingestion_events` are reserved for later phases.

## 9. Cloud Inference Rules

Device id:

```text
capture.device_id
fallback video.device_id
fallback source.source_host
fallback unknown
```

Local analyzer:

```text
source.source_host
fallback upload.source_host
fallback unknown
```

Capture time:

```text
capture.captured_at
fallback time.recorded_at
fallback generated_at
fallback created_at
```

Upload/receive time:

```text
upload.uploaded_at
fallback analysis_results.created_at
fallback time.generated_at
```

Video state:

```text
video.video_url exists -> playable
video.raw_video_path or capture.video_path exists -> pending
none -> missing
```

Device freshness:

```text
within 24h -> online
within 7d -> stale
older than 7d -> offline
missing timestamp -> unknown
```

The page must label this as inferred from latest upload time.

## 10. API Design

Add page:

```http
GET /admin/ingestion
```

Add API:

```http
GET /api/admin/ingestion
```

Parameters:

- `classroom_id`
- `device_id`
- `source_host`
- `days`
- `limit`

Expected response:

```json
{
  "success": true,
  "filters": {},
  "overview": {},
  "pipeline": [],
  "devices": [],
  "recent_ingestions": [],
  "video_summary": {},
  "validation_hints": []
}
```

No new POST endpoint is required. Local analyzer continues using:

```http
POST /api/interaction-results
```

## 11. Page Design

`/admin/ingestion` must include:

- Admin Console navigation
- ingestion status hero
- Capture -> Local Analysis -> Cloud Storage -> Teacher Feedback pipeline
- metric cards
- filters
- device/analyzer status list
- recent ingestion records
- video readiness summary
- validation/data-quality hints

The page must be visually complete and not table-only.

## 12. Validation Criteria

Raspberry Pi contract:

- capture metadata JSON is valid
- required capture fields exist

Local analyzer contract:

- uploaded JSON contains `source`, `capture`, `video`, `upload`
- existing analysis fields remain present
- cloud upload succeeds
- video format capability audit is recorded

Cloud:

- `/admin/ingestion` returns `200`
- `/api/admin/ingestion` returns required keys
- ingestion page shows pipeline, devices, records, video summary, hints
- existing Phase 1/2/2.5/2.6/2.7 behavior does not regress

## 13. Risks

- Scope may expand into device management.
- Inferred freshness may be mistaken for true online status.
- Local video format audit may uncover missing capability but should not block cloud page.
- Older payloads may lack new metadata and require fallback.
- Three-side work needs separate prompts and validation.

