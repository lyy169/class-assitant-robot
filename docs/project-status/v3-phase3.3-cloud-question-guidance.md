# V3 Phase 3.3 Cloud Teacher Question Guidance Status

## Status

Implementation and runtime validation completed.

Phase 3.3 is a cloud compatibility/display phase only:

- Upload API changed: no.
- New mandatory API added: no.
- Database migration: no.
- Permission model changed: no.
- Raspberry Pi or local analyzer changed: no.
- Git closeout: prepared for the Phase 3.3 closeout commit.

## Modified Files

- `cloud_backend/postgres_repository.py`
- `cloud_backend/dashboard_v11.py`
- `cloud_backend/teacher_pages.py`
- `samples/phase3_3_question_guidance_result.json`
- `scripts/validate_phase3_3_cloud_question_guidance.sh`
- `docs/runbooks/v3-phase3.3-cloud-question-guidance-validation-runbook.md`
- `docs/project-status/v3-phase3.3-cloud-question-guidance.md`

## Compatibility Behavior

`POST /api/interaction-results` remains unchanged. The existing payload model allows extra fields, so `teacher_question_events` and `question_guidance_summary` can be uploaded without schema changes.

Raw JSON preservation remains unchanged. The new fields are preserved in the raw JSON file and PostgreSQL `payload_json`.

Detail API behavior:

- `GET /api/teacher/results/{result_id}` keeps the same response envelope.
- When present, `teacher_question_events` and `question_guidance_summary` are exposed at result level and under `phase33`.
- Old data without the fields continues to render without errors.

Report detail behavior:

- `GET /api/teacher/reports/detail?result_id=<result_id>` keeps the same response envelope.
- When present, question guidance fields are exposed as `report.teacher_question_events`, `report.question_guidance_summary`, and `report.phase33`.

## Page Display

`/dashboard` now shows a Phase 3.3 teacher question guidance block when fields exist:

- Question count.
- Guidance score.
- Open / closed / check distribution.
- Early / middle / late coverage.
- Teacher question timeline and examples.
- Response signal summary.
- Main issue, evidence, and suggestion.
- Demo label when source/status indicates `demo` or `demo_seed`.

`/teacher/reports?result_id=<result_id>` now shows teaching-guidance analysis when fields exist:

- Question summary.
- Question distribution.
- Guidance score.
- Main issue.
- Evidence.
- Suggestion.
- Question examples.

AI summary remains optional and is not faked by this phase.

## Validation

Static check:

```text
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
```

Static result:

```text
passed
```

Runtime command:

```bash
cd /root/video_project_src
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_3_cloud_question_guidance.sh
```

Expected markers:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_TEACHER_LOGIN_OK=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
PHASE33_REGRESSION_OK=true
```

Runtime result:

```text
passed on cloud server, confirmed by user
```

Actual runtime markers:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_TEACHER_LOGIN_OK=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
PHASE33_REGRESSION_OK=true
```

Raw saved path:

```text
/root/video_project_src/cloud_backend/data/raw/2026-05-06/phase3_3_question_guidance_sample_001.json
```

## Browser Acceptance URLs

```text
http://<server>:8011/dashboard?result_id=phase3_3_question_guidance_sample_001
http://<server>:8011/teacher/reports?result_id=phase3_3_question_guidance_sample_001
```

## Residual Risks

- The sample file is under `samples/`, which is ignored by `.gitignore`; Phase 3.3 closeout should stage it explicitly because the validation script depends on it.
- Runtime validation requires PostgreSQL runtime and Phase 2.9 auth seed users; the successful markers above were produced in that environment.
- This phase only displays teacher question guidance; it does not generate transcript or question analysis itself.
