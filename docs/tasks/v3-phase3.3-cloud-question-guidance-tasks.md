# V3 Phase 3.3 Tasks: Cloud Teacher Question Guidance Display

## 1. Discovery

- [ ] Check `git status --short`.
- [ ] Read `docs/specs/v3-phase3.3-cloud-question-guidance-spec.md`.
- [ ] Locate upload/raw preservation code.
- [ ] Locate detail API mapping.
- [ ] Locate `/dashboard` rendering code.
- [ ] Locate `/teacher/reports` rendering code.

## 2. API Compatibility

- [ ] Confirm upload API route unchanged.
- [ ] Confirm raw JSON preserves `teacher_question_events` and `question_guidance_summary`.
- [ ] Ensure detail API exposes these fields when present.
- [ ] Ensure old data without fields still works.
- [ ] Do not migrate database.

## 3. Dashboard UI

- [ ] Add question guidance block only when fields exist or unavailable summary exists.
- [ ] Show question count and guidance score.
- [ ] Show open/closed/check distribution.
- [ ] Show early/middle/late coverage.
- [ ] Show question timeline/examples.
- [ ] Show main issue and suggestion.
- [ ] Label demo data when source/status indicates demo.

## 4. Reports UI

- [ ] Add teaching-guidance analysis in report detail.
- [ ] Show question summary, evidence, and suggestion.
- [ ] Degrade safely if fields missing.
- [ ] Do not pretend AI summary exists.

## 5. Sample and Validation

- [ ] Add or copy `samples/phase3_3_question_guidance_result.json`.
- [ ] Add `scripts/validate_phase3_3_cloud_question_guidance.sh`.
- [ ] Validate upload.
- [ ] Validate raw preservation.
- [ ] Validate detail fields.
- [ ] Validate dashboard/reports HTTP access.

## 6. Documentation

- [ ] Create/update `docs/runbooks/v3-phase3.3-cloud-question-guidance-validation-runbook.md`.
- [ ] Create/update `docs/project-status/v3-phase3.3-cloud-question-guidance.md`.

## 7. Output

Final CLI output should include:

- Modified files.
- API/DB unchanged confirmation.
- Displayed fields.
- Validation commands/results.
- `git status --short`.
- No git commit unless explicitly requested.
