# Phase 3.17 Frontend Sample Scope CLI Prompt

Work in `/root/video_project_src`.

Goal: close the frontend presentation scope for the competition demo. The final frontend sample is `phase314_asr_full_classroom_sav_20200908_17`. It is the ASR-enhanced full-classroom SAV sample and must be labeled as an external public SAV classroom video processed by the local analyzer, not Raspberry Pi capture and not self-captured data.

Required behavior:

- Keep `phase314_asr_full_classroom_sav_20200908_17` visible as the final ASR-enhanced full-classroom sample.
- Hide `phase37_full_classroom_sav_20200908_17` from default formal report/trend/teacher/admin lists as a historical phase sample.
- Hide `phase35_local_imported_sav_full_classroom_20200908_17` from default formal lists as a playback smoke test.
- Hide `cls_20260430_classroom_101_d4b91cf9c0bf4e68bfcb5e12933d30ee` and `cls_20260429_classroom_101_c993e071203b44e1bef1db1586181503` as legacy all-zero test records.
- Hide `cls_20260417_101_001` / `video_20260417_001` from default competition report/trend views, or expose it only with an explicit legacy visual-only label.
- Label demo data when demo/all filters include it.
- Do not delete database data.
- Do not re-upload video.
- Do not modify core visual algorithms.
- Do not modify local analyzer or Raspberry Pi code.
- Do not commit git.

Trusted metrics for the final ASR sample:

- Video evidence.
- Transcript segments: `764`.
- Teacher question candidates: `35`.
- Visual response alignments: `35`.
- Detected responses: `16`.
- Response rate: about `45.7%`.
- Activity curve and hand-raise events where available.

Do not promote unavailable metrics:

- Attention score `0`.
- Average attention `0`.
- Student count `0`.
- All-zero stage distribution.
- `audio=false` debug evidence.

Validation:

```bash
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/dashboard_v11.py cloud_backend/main.py
bash -n scripts/validate_phase3_17_frontend_sample_scope.sh
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_17_frontend_sample_scope.sh
```
