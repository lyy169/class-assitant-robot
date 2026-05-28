# V3 Phase 3.6a CLI Prompt Summary

Implement the cloud-side automatic video plus analysis JSON receiving path.

Required endpoint:

```text
POST /api/interaction-results/with-video
```

The endpoint accepts `multipart/form-data` with:

- `result_json`: analysis JSON file field.
- `video_file`: classroom video file.

Implementation boundaries:

- Keep existing `POST /api/interaction-results`.
- Reuse `InteractionResultPayload`, raw JSON save, and active repository save.
- Save videos to `settings.video_upload_dir`.
- Generate `/uploads/<safe_video_filename>` and inject it into `payload["video"]["video_url"]`.
- Do not infer video duration.
- Do not add database migration.
- Do not rewrite dashboard.
- Do not modify Raspberry Pi or local analyzer algorithms.
- Do not start or restart services automatically.
- Do not commit git changes.

Validation:

- Add `scripts/validate_phase3_6_with_video_upload.sh`.
- Use the Phase 3.5 one-minute package as a smoke test only.
- Output all `PHASE36_*` markers.

Important product boundary:

- 50 SAV clips are not a single complete classroom dashboard.
- The one-minute demo clip is not the final competition sample.
- Phase 3.7 must validate a same-source full-classroom video and same-source full analysis JSON.
