# V3 Phase 3.8 Runbook: Dashboard Display Scope Validation

## Purpose

Validate that the final competition dashboard sample presents its source and metric scope accurately.

Final sample:

```text
phase37_full_classroom_sav_20200908_17
```

Dashboard:

```text
http://<server>:8011/dashboard?result_id=phase37_full_classroom_sav_20200908_17
```

## Static Validation

Run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/dashboard_v11.py cloud_backend/postgres_repository.py
bash -n scripts/validate_phase3_8_dashboard_display_scope.sh
```

## Runtime Validation

If the cloud service is already running old code, manually restart it first. This runbook does not start or restart services automatically.

Then run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_8_dashboard_display_scope.sh
```

## Expected Markers

```text
PHASE38_DETAIL_API_OK=true
PHASE38_DISPLAY_SCOPE_PRESENT=true
PHASE38_FINAL_SAMPLE_SOURCE_NOTE_PRESENT=true
PHASE38_FINAL_SAMPLE_NOT_PI_CAPTURE=true
PHASE38_FINAL_SAMPLE_NOT_OWN_CAPTURE=true
PHASE38_DEMO_CLIP_SCOPE_NOTE_SUPPORTED=true
PHASE38_UNSUPPORTED_METRICS_MARKED=true
PHASE38_NO_1MIN_VIDEO_FULL_CLASS_MISLEADING=true
PHASE38_NO_SAV50_MIXED_IN_DASHBOARD=true
PHASE38_DASHBOARD_REACHABLE=true
PHASE38_DASHBOARD_DISPLAY_SCOPE_OK=true
```

## Browser Check

Open:

```text
http://<server>:8011/dashboard?result_id=phase37_full_classroom_sav_20200908_17
```

Verify:

- The source note says the sample comes from SAV external public classroom video.
- The page does not imply Raspberry Pi capture or self-capture for the SAV sample.
- Audio/transcript/question-related metrics are marked as structural display only when evidence is unavailable.
- The one-minute demo clip is not presented as the final full-classroom sample.
