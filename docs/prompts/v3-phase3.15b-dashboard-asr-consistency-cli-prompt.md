# V3 Phase 3.15b Dashboard ASR Consistency CLI Prompt

Implement a narrow cloud-side hotfix for ASR-enhanced dashboard consistency.

Target sample:

```text
phase314_asr_full_classroom_sav_20200908_17
```

Required fixes:

- Override display summary when ASR transcript and question candidates are present.
- Hide or bypass legacy Phase 3.3 no-transcript/no-question wording for ASR-enhanced samples.
- Replace the SAV scope note that says classroom transcript is not connected with wording that says local offline ASR transcript exists, while Raspberry Pi voice trigger and speaker diarization are not connected.
- Do not fake attention, heat, or stage data. Show explicit low-confidence/empty-state notes when these arrays are all zero.
- Keep activity curve visible.
- Show ASR question candidates in event distribution.
- Add data-quality note to teacher report/trends/admin contexts for external SAV ASR samples.
- Change admin ingestion pipeline wording from Raspberry Pi-only capture to capture endpoint or external sample.
- Fix `analysis_version` template escaping.

Forbidden:

- Do not modify database schema.
- Do not modify upload endpoints.
- Do not modify local-side or Raspberry Pi code.
- Do not rewrite dashboard.
- Do not fabricate scores or curves.
- Do not commit git.

Validation:

```bash
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/dashboard_v11.py cloud_backend/admin_pages.py cloud_backend/teacher_pages.py
bash -n scripts/validate_phase3_15b_dashboard_asr_consistency.sh
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15b_dashboard_asr_consistency.sh
```
