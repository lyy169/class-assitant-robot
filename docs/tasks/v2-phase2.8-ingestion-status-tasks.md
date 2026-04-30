# V2 Phase 2.8 Tasks: Three-Side Ingestion Status

## Principles

- Three-side metadata contract first.
- Cloud implementation must be metadata-driven.
- Raspberry Pi and server projects may be edited through SSHFS, but runtime/device operations must be provided as scripts for the operator to run on the target machine.
- Do not add core database tables.
- Do not modify raw JSON.
- Do not implement device CRUD, heartbeat, or video upload.
- Do not implement new video transcoding.
- Preserve Phase 1/2/2.5/2.6/2.7 behavior.

## Task 1: Read SDD Documents

Read:

- `docs/specs/v2-phase2.8-ingestion-status-spec.md`
- `docs/specs/v2-phase2.8-pi-capture-contract.md`
- `docs/specs/v2-phase2.8-local-session-upload-contract.md`

Confirm the executor is working on the correct side:

- Raspberry Pi side
- local analyzer side
- cloud side

## Task 2: Raspberry Pi Side Metadata Support

Owner: Raspberry Pi project.

Implement or verify:

- `capture_metadata.json` generation
- `capture.device_id`
- `capture.classroom_id`
- `capture.captured_at`
- optional `device_name`, `video_path`, `keyframe_dir`

Validation:

- output PI capture markers from contract document
- provide a Raspberry Pi-side validation script, recommended `scripts/validate_capture_metadata.sh`
- document the exact command that the operator should run on the Raspberry Pi device
- do not rely on Codex running camera or hardware checks from the SSHFS-mounted workspace

## Task 3: Local Analyzer Metadata Merge

Owner: local analyzer project.

Implement or verify:

- read capture metadata
- merge `source`
- merge `capture`
- merge `video`
- merge `upload`
- preserve existing V1.1 analysis fields
- preserve teacher question events/summary when available

Validation:

- output local session/upload markers from contract document
- upload JSON successfully to cloud

## Task 4: Local Video Format Capability Audit

Owner: local analyzer project.

Audit whether video standardization already exists.

Check for:

- ffmpeg
- moviepy
- cv2 VideoWriter
- subprocess ffmpeg
- standardize/convert/transcode scripts

Do not implement new transcoding unless separately requested.

Validation markers:

- `LOCAL_VIDEO_TRANSCODE_CAPABILITY=present/absent/unknown`
- `LOCAL_VIDEO_OUTPUT_BROWSER_COMPATIBLE=true/false/unknown`

## Task 5: Cloud Ingestion Repository Aggregation

Owner files:

- `cloud_backend/postgres_repository.py`

Add method:

```text
get_admin_ingestion(classroom_id=None, device_id=None, source_host=None, days=30, limit=20)
```

Return:

- filters
- overview
- pipeline
- devices
- recent_ingestions
- video_summary
- validation_hints

Use only existing tables and `payload_json`.

## Task 6: Cloud Admin Ingestion API

Owner file:

- `cloud_backend/auth.py` or admin router module

Add:

```text
GET /api/admin/ingestion
```

Parameters:

- classroom_id
- device_id
- source_host
- days
- limit

Validation:

- returns required keys
- empty data is safe

## Task 7: Cloud Admin Ingestion Page

Owner files:

- `cloud_backend/main.py`
- `cloud_backend/admin_pages.py`

Add:

```text
GET /admin/ingestion
```

Required modules:

- Admin Console navigation
- ingestion status hero
- Capture -> Local Analysis -> Cloud Storage -> Teacher Feedback pipeline
- metric cards
- filters
- device/analyzer list
- recent ingestion records
- video readiness summary
- validation/data-quality hints

## Task 8: Update Admin Navigation

Owner file:

- `cloud_backend/admin_pages.py`

Add `Ingestion Status` link to Admin Console navigation.

Do not break existing admin pages.

## Task 9: Add Cloud Validation Script

Owner file:

- `scripts/validate_phase2_8_ingestion_status.sh`

Validate:

- `/admin/ingestion`
- `/api/admin/ingestion`
- required API keys
- ingestion page markers
- Phase 2.7 admin pages
- Phase 2.6 teacher pages
- Phase 2.5 dashboard
- Phase 1/2 latest/recent APIs

Emit true/false markers.

## Task 10: Add Three-Side Runbook

Owner file:

- `docs/runbooks/v2-phase2.8-three-side-validation-runbook.md`

Document:

- Raspberry Pi metadata validation
- local analyzer metadata validation
- local upload command
- cloud ingestion API validation
- cloud ingestion page validation
- regression checks

## Task 11: Update Project Status

Owner file:

- `docs/project-status/v2-phase2.8-ingestion-status.md`

Record:

- implemented side
- implemented files
- validation results
- metadata contract compliance
- remaining side work

## Task 12: Regression

Confirm:

- Phase 2.7 admin console
- Phase 2.6 teacher home/results
- Phase 2.5 dashboard/detail
- Phase 1/2 upload/read
