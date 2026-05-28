# V3 Phase 3.5c Runbook: Local-to-Cloud Playback Integration

## Goal

Phase 3.5c validates that a classroom video clip and analysis JSON exported by the local analyzer can be sent to the cloud server and displayed together in `/dashboard`.

Recommended wording:

- Local-to-cloud send integration.
- Cloud receives local analysis results.
- Cloud video playback validation.

Avoid wording this phase as a cloud import feature. The local side produces the package; the operator sends the files to the cloud runtime.

## Non-Goals

This phase does not:

- Add a new API.
- Run a database migration.
- Rewrite the dashboard structure.
- Modify the local core algorithm.
- Modify the Raspberry Pi side.
- Describe the SAV source as Raspberry Pi capture or self-captured footage.
- Use a 576 MB full raw video as the default demo asset.
- Commit git changes.

## Source Package

Local package path:

```text
C:\Users\lyy\Desktop\gradu\phase35_cloud_upload_package\phase35_local_imported_sav_full_classroom_20200908_17
```

Expected files:

```text
phase35_demo_classroom_101.mp4
phase35_cloud_upload_result.json
package.json
local_imported_full_classroom_summary.csv
local_imported_full_classroom_validation_report.md
```

## Manual Staging Step

The operator must manually copy the full package to this cloud staging directory:

```text
/root/video_project_src/cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17
```

This staging directory is runtime data and must not be committed to git.

## Send Package To Cloud Runtime

After copying the package, run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
bash scripts/phase3_5_send_local_package_to_cloud.sh
```

Optional custom staging directory:

```bash
bash scripts/phase3_5_send_local_package_to_cloud.sh \
  --staging-dir /root/video_project_src/cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17
```

Optional custom API base URL:

```bash
bash scripts/phase3_5_send_local_package_to_cloud.sh \
  --api-base-url http://127.0.0.1:8011
```

If the target video already exists, the script reuses it by default. To overwrite it:

```bash
bash scripts/phase3_5_send_local_package_to_cloud.sh --overwrite-video
```

The send script:

- Reads `package.json`, `phase35_demo_classroom_101.mp4`, and `phase35_cloud_upload_result.json` from staging.
- Copies the MP4 to `/root/video_project/uploads/phase35_demo_classroom_101.mp4`.
- Posts JSON to `POST /api/interaction-results`.
- Saves the upload response under the staging directory.
- Verifies the static `/uploads/phase35_demo_classroom_101.mp4` URL.

The send script does not modify business code, modify database structure, restart services, edit systemd, print secrets, or commit git changes.

## Validate Cloud Playback

After sending the package, run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
bash scripts/validate_phase3_5_local_to_cloud_playback.sh
```

The validation script checks:

- `/health`
- `/uploads/phase35_demo_classroom_101.mp4`
- Teacher login.
- `/api/teacher/results/phase35_local_imported_sav_full_classroom_20200908_17`
- `video.status=playable`
- `video.video_url=/uploads/phase35_demo_classroom_101.mp4`
- `/dashboard?result_id=phase35_local_imported_sav_full_classroom_20200908_17`
- `/teacher/reports?result_id=phase35_local_imported_sav_full_classroom_20200908_17`
- Admin login.
- `/admin/ingestion`
- `/api/admin/ingestion?classroom_id=classroom_101`

## Browser Acceptance URLs

```text
http://<server>:8011/dashboard?result_id=phase35_local_imported_sav_full_classroom_20200908_17
http://<server>:8011/teacher/reports?result_id=phase35_local_imported_sav_full_classroom_20200908_17
http://<server>:8011/admin/ingestion
```

## Expected Video Mapping

Cloud video target path:

```text
/root/video_project/uploads/phase35_demo_classroom_101.mp4
```

Cloud video URL:

```text
/uploads/phase35_demo_classroom_101.mp4
```

The local analyzer JSON should include:

```json
{
  "video": {
    "video_url": "/uploads/phase35_demo_classroom_101.mp4"
  }
}
```

