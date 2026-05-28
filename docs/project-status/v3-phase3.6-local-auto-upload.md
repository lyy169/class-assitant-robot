# V3 Phase 3.6a Local Auto Upload Status

## Status

Runtime smoke validation passed.

This round:

- Added cloud multipart upload endpoint.
- Preserved existing JSON-only upload endpoint.
- Added smoke validation script.
- Added SDD docs and runbook.
- Service restart was handled manually by the operator before runtime validation.
- Did not modify systemd.
- Did not change database schema.
- Did not commit git changes.

## Endpoint

```text
POST /api/interaction-results/with-video
```

Request:

- `result_json`: JSON file field, with string fallback supported.
- `video_file`: `.mp4`, `.webm`, `.mov`, or `.ogg`.

Response:

- `success`
- `request_id`
- `saved_path`
- `video_url`
- `video_path`
- `analysis_id`

## Runtime Boundary

The validation script uses the Phase 3.5 one-minute package as an endpoint smoke test only.

It does not prove final full classroom analysis quality. Phase 3.7 must use a same-source full-classroom video and same-source full JSON.

## Static Validation

Commands requested:

```bash
python -B -m py_compile cloud_backend/main.py
bash -n scripts/validate_phase3_6_with_video_upload.sh
```

Result:

```text
bash -n scripts/validate_phase3_6_with_video_upload.sh: passed
python -B -m py_compile cloud_backend/main.py: blocked in SSHFS CLI by [WinError 5] writing cloud_backend/__pycache__
equivalent no-project-write py_compile check for cloud_backend/main.py: passed
python-multipart dependency: present in cloud_backend/requirements.txt
forbidden action scan for service restart, git add/commit, and database DDL/DML: no matches
```

Operator note:

- The exact `python -B -m py_compile cloud_backend/main.py` command should be rerun directly on the cloud server if strict command parity is required.
- It was not completed from this SSHFS CLI because Python attempted to write a local `__pycache__` file and the mount denied access.

## Runtime Validation

Command run by operator:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_6_with_video_upload.sh
```

Result:

```text
PHASE36_WITH_VIDEO_ENDPOINT_PRESENT=true
PHASE36_HEALTH_OK=true
PHASE36_STAGING_PACKAGE_PRESENT=true
PHASE36_MULTIPART_UPLOAD_HTTP_OK=true
PHASE36_MULTIPART_UPLOAD_SUCCESS=true
PHASE36_CLOUD_VIDEO_SAVED=true
PHASE36_CLOUD_RAW_JSON_SAVED=true
PHASE36_RESPONSE_VIDEO_URL_PRESENT=true
PHASE36_STATIC_VIDEO_OK=true
PHASE36_TEACHER_DETAIL_OK=true
PHASE36_DETAIL_VIDEO_URL_MATCH=true
PHASE36_DASHBOARD_REACHABLE=true
PHASE36_NO_MANUAL_VIDEO_COPY_REQUIRED=true
PHASE36_DEMO_CLIP_NOT_FINAL_SAMPLE=true
PHASE36_LOCAL_AUTO_UPLOAD_CLOUD_READY=true
```

## Closeout Summary

Phase 3.6a confirms that the cloud can receive a multipart package containing video plus analysis JSON, save the video automatically, inject `video.video_url`, persist raw JSON, index the result, and display the uploaded video through existing dashboard/detail paths.

This does not close the final full-classroom sample requirement. Phase 3.7 remains responsible for using same-source full-classroom video and same-source full analysis JSON for the final competition dashboard sample.
