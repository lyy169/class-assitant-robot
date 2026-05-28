# V3 Phase 3.15c Dashboard Hide Unavailable Metrics CLI Prompt

Implement a narrow cloud dashboard display hotfix for:

```text
phase314_asr_full_classroom_sav_20200908_17
```

Goal:

- Hide unavailable or unsupported visual metrics from the ASR-enhanced SAV dashboard.
- Focus the page on complete video, ASR transcript summary, teacher question candidates, visual response alignment, activity curve, hand-raise events, and source/boundary notes.

Required:

- Hide attention KPI, average attention ratio, estimated student count, attention curve, region attention, and teaching stage distribution for the ASR SAV sample.
- Hide Phase 3.2 score breakdown and legacy enhanced issue scoring from the main dashboard for this sample.
- Keep activity curve and question candidate markers.
- Keep event distribution and question candidates.
- Do not fabricate attention, student count, or stage values.
- Add or use additive `display_flags` only; do not change raw payload.

Forbidden:

- Do not modify database schema.
- Do not modify upload APIs.
- Do not modify local analyzer or Raspberry Pi code.
- Do not generate ASR rule-based teaching stages.
- Do not commit git.

Validation:

```bash
python -B -m py_compile cloud_backend/dashboard_v11.py cloud_backend/postgres_repository.py
bash -n scripts/validate_phase3_15c_dashboard_hide_unavailable_metrics.sh
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15c_dashboard_hide_unavailable_metrics.sh
```
