# V3 Phase 3.6a Tasks: Local Auto Upload To Cloud

## Task 1: Preserve Existing JSON Upload

- Keep `POST /api/interaction-results` behavior and response compatible.
- Extract shared payload validation, raw persistence, and repository indexing into a helper.
- Reuse the helper from both JSON-only and multipart endpoints.

Acceptance:

- Existing JSON upload route still compiles and returns `ApiResponse`.
- No dashboard or database schema rewrite.

## Task 2: Add Multipart With-Video Endpoint

- Add `POST /api/interaction-results/with-video`.
- Accept `result_json` and `video_file`.
- Apply the same API key behavior as the old endpoint.
- Validate allowed video suffixes.
- Save video to `settings.video_upload_dir`.
- Inject `video.video_url`.
- Persist raw JSON and index via existing repository.

Acceptance:

- Response includes `success`, `request_id`, `saved_path`, `video_url`, `video_path`, and `analysis_id`.
- `video.video_url` in teacher detail matches the upload response.
- No manual copy to `/root/video_project/uploads` is required during smoke validation.

## Task 3: Add Validation Script

- Add `scripts/validate_phase3_6_with_video_upload.sh`.
- Use the existing Phase 3.5 one-minute package for smoke test only.
- Upload using `curl -F`.
- Verify health, endpoint, saved video, saved raw JSON, static video URL, teacher detail, and dashboard reachability.

Acceptance markers:

- `PHASE36_WITH_VIDEO_ENDPOINT_PRESENT=true`
- `PHASE36_MULTIPART_UPLOAD_SUCCESS=true`
- `PHASE36_CLOUD_VIDEO_SAVED=true`
- `PHASE36_CLOUD_RAW_JSON_SAVED=true`
- `PHASE36_DETAIL_VIDEO_URL_MATCH=true`
- `PHASE36_NO_MANUAL_VIDEO_COPY_REQUIRED=true`
- `PHASE36_LOCAL_AUTO_UPLOAD_CLOUD_READY=true`

## Task 4: Document Runtime Boundary

- Document that Phase 3.6a prepares the cloud-side auto upload endpoint.
- Document that the current smoke clip is not final competition data.
- Document that Phase 3.7 will validate final same-source full video plus full JSON.

Acceptance:

- Spec, tasks, runbook, project status, and prompt docs are present.
- Static validation results are recorded.
