# V3 Phase 3.3 Spec: Cloud Teacher Question Guidance Display

## 1. Goal

Cloud Phase 3.3 should consume teacher question guidance fields from uploaded classroom feedback JSON and display teacher questioning as teaching-guidance evidence.

Network API remains unchanged.

## 2. Non-Goals

- Do not rewrite `POST /api/interaction-results`.
- Do not add mandatory API routes.
- Do not migrate database.
- Do not modify Raspberry Pi or local analyzer code.
- Do not assume teacher questions always exist.

## 3. Input Fields

Optional fields in final classroom feedback JSON:

```text
teacher_question_events
question_guidance_summary
```

Old data may not contain these fields. Pages must degrade safely.

## 4. API Compatibility

Upload API remains:

```text
POST /api/interaction-results
```

Detail API remains:

```text
GET /api/teacher/results/{result_id}
```

Cloud requirements:

- raw JSON preserves question guidance fields.
- detail API returns or exposes question guidance fields when present.
- recent API remains lightweight.
- status API unchanged.

No database migration in this phase.

## 5. Dashboard Display

In `/dashboard`, when fields exist, show a teacher-question guidance block:

- question count
- guidance score
- open/closed/check distribution
- early/middle/late coverage
- teacher question timeline
- Top question examples
- response signal summary
- main issue and suggestion

When unavailable:

- show friendly note: teacher question transcript unavailable.
- do not show error.

## 6. Report Display

In `/teacher/reports`, when fields exist, show teaching-guidance analysis:

- teacher question summary
- question distribution
- guidance score
- main issue
- evidence
- suggestion

If source is `demo_seed` or status is `demo`, label it as demo data.

## 7. Validation

Add validation script:

```text
scripts/validate_phase3_3_cloud_question_guidance.sh
```

Expected markers:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
```

## 8. Status Document

Implementation should write/update:

```text
docs/project-status/v3-phase3.3-cloud-question-guidance.md
```
