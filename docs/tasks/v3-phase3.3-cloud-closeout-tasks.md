# V3 Phase 3.3 Tasks: Cloud Closeout

## 1. Preparation

- [ ] Enter `/root/video_project_src`.
- [ ] Read `docs/specs/v3-phase3.3-cloud-closeout-spec.md`.
- [ ] Read `docs/project-status/v3-phase3.3-cloud-question-guidance.md`.
- [ ] Run `git status --short`.
- [ ] Separate Phase 3.3 files from historical dirty files.

## 2. Validation

- [ ] Run static validation:

```bash
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
```

- [ ] Rerun runtime validation if service is available:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_3_cloud_question_guidance.sh
```

- [ ] At minimum, update status document with user-confirmed markers:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_TEACHER_LOGIN_OK=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
PHASE33_REGRESSION_OK=true
```

## 3. Status Documentation

- [ ] Update `docs/project-status/v3-phase3.3-cloud-question-guidance.md` so runtime result is not pending.
- [ ] Record raw saved path if available:

```text
/root/video_project_src/cloud_backend/data/raw/2026-05-06/phase3_3_question_guidance_sample_001.json
```

- [ ] Keep residual risks honest.

## 4. Stage Files

Explicitly stage Phase 3.3 cloud files:

```bash
git add cloud_backend/postgres_repository.py
git add cloud_backend/dashboard_v11.py
git add cloud_backend/teacher_pages.py
git add scripts/validate_phase3_3_cloud_question_guidance.sh
git add docs/specs/v3-phase3.3-cloud-question-guidance-spec.md
git add docs/tasks/v3-phase3.3-cloud-question-guidance-tasks.md
git add docs/prompts/v3-phase3.3-cloud-question-guidance-cli-prompt.md
git add docs/runbooks/v3-phase3.3-cloud-question-guidance-validation-runbook.md
git add docs/project-status/v3-phase3.3-cloud-question-guidance.md
git add docs/specs/v3-phase3.3-cloud-closeout-spec.md
git add docs/tasks/v3-phase3.3-cloud-closeout-tasks.md
git add docs/prompts/v3-phase3.3-cloud-closeout-cli-prompt.md
```

If sample file is ignored but required:

```bash
git add -f samples/phase3_3_question_guidance_result.json
```

If not ignored:

```bash
git add samples/phase3_3_question_guidance_result.json
```

## 5. Commit

- [ ] Run `git diff --cached --stat`.
- [ ] Confirm only Phase 3.3 cloud files are staged.
- [ ] Commit:

```bash
git commit -m "feat(cloud): display phase 3.3 question guidance"
```

## 6. Output

- [ ] Static validation result.
- [ ] Runtime validation markers.
- [ ] Whether status doc was updated.
- [ ] Commit hash.
- [ ] Committed files.
- [ ] Remaining `git status --short` and whether residual files are historical.
