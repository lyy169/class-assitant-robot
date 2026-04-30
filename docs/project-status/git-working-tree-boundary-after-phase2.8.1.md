# Git Working Tree Boundary After Phase 2.8.1

## 1. Snapshot

Date: 2026-04-30

Current branch:

```text
chore/cloud-src-bootstrap
```

Latest committed Phase 2.5-2.8.1 baseline:

```text
290bbaa feat(cloud): add teacher admin dashboards and ingestion visibility
```

Full hash:

```text
290bbaa12d3c403195f066fe50fab6622ed09c1f
```

## 2. Phase 2.8.1 Submitted Scope

The latest commit contains the accepted cloud-side baseline for:

- Phase 2.5 teacher classroom analysis center `/dashboard`
- Phase 2.6 teacher home and classroom records `/teacher`, `/teacher/results`
- Phase 2.7 admin console `/admin`, `/admin/classrooms`, `/admin/teachers`, `/admin/results`
- Phase 2.8 ingestion status `/admin/ingestion`
- Phase 2.8.1 standardized video metadata compatibility in ingestion status
- validation scripts for Phase 2 result workbench through Phase 2.8 ingestion status
- SDD specs, tasks, runbooks, and project-status documents for the submitted phases

## 3. Current Uncommitted Files

Current `git status --short` still contains historical and out-of-scope files. They were intentionally not included in the Phase 2.5-2.8.1 commit.

```text
 M README.md
 M cloud_backend/README.md
 M cloud_backend/RUNBOOK.md
 M cloud_backend/__init__.py
 M cloud_backend/classroom-cloud-backend.service.example
 M cloud_backend/logging_utils.py
 M cloud_backend/schemas.py
 M docs/change_logs/2026-04-15_云端接收服务搭建与联调.md
 M docs/change_logs/README.md
 M docs/changes/README.md
 M docs/plans/README.md
 M docs/plans/cloud-git-convergence-plan.md
 M docs/plans/cloud-legacy-boundary.md
 M docs/plans/cloud-service-boundary.md
 M docs/plans/cloud-src-bootstrap-checklist.md
 M docs/plans/cloud-src-copy-manifest.md
 M docs/plans/cloud-src-path-decision.md
 M docs/plans/video-project-src-blueprint.md
 M docs/runbooks/cloud-src-bootstrap-runbook.md
 M docs/specs/README.md
 M docs/tasks/cloud-convergence-next-steps.md
 M scripts/.gitkeep
 M scripts/README.md
 M scripts/bootstrap_cloud_src.sh
 M scripts/deploy_cloud_backend.sh
 M scripts/templates/cloud_src_README.md.template
 M scripts/templates/cloud_src_gitignore.template
 M scripts/test_cloud_backend.sh
?? cloud_backend/dashboard.py
?? docs/plans/cloud-capability-integration-map.md
?? docs/plans/cloud-data-model-plan.md
?? docs/plans/cloud-results-center-plan.md
?? docs/project-status/cloud-backend-capability-status.md
?? docs/project-status/cloud-current-architecture-survey.md
?? docs/project-status/cloud-runtime-hardening-iteration-02.md
?? docs/project-status/cloud-runtime-hardening-iteration-03.md
?? docs/project-status/cloud-runtime-observability-baseline.md
?? docs/project-status/cloud-runtime-steady-state-iteration-02.md
?? docs/project-status/cloud-sqlite-repository-iteration-01.md
?? docs/project-status/cloud-steady-state-choice-template.md
?? docs/project-status/pi-real-device-validation-prep.md
?? docs/project-status/pi-session-delivery-iteration-01.md
?? docs/project-status/v2-phase2-result-workbench.md
?? docs/project-status/v2-phase2.5-polish-plan.md
?? docs/runbooks/cloud-real-upload-validation-v1.md
?? docs/runbooks/cloud-results-center-validation-runbook.md
?? docs/runbooks/cloud-results-dashboard-runbook.md
?? docs/runbooks/cloud-runtime-and-sqlite-deploy-v1.md
?? docs/runbooks/pi-real-device-validation-v1.md
?? docs/specs/cloud-storage-repository-v1.md
?? docs/specs/pi-session-delivery-v1.md
?? docs/tasks/cloud-capability-integration-next-steps.md
?? scripts/check_cloud_runtime_observability.sh
?? scripts/setup_postgres_schema.sh
?? scripts/upload_real_result.sh
?? scripts/validate_auth.sh
?? scripts/validate_cloud_results_center.sh
?? scripts/validate_postgres.sh
?? scripts/validate_teacher_api.sh
?? 行为规则.md
```

## 4. Uncommitted File Classification

### 4.1 Historical Cloud Infrastructure / README / RUNBOOK Changes

These files appear to be historical cloud bootstrap, deployment, or baseline documentation changes. They are not part of the Phase 2.5-2.8.1 accepted feature commit and should not be swept into Phase 2.9.

```text
README.md
cloud_backend/README.md
cloud_backend/RUNBOOK.md
cloud_backend/__init__.py
cloud_backend/classroom-cloud-backend.service.example
cloud_backend/logging_utils.py
cloud_backend/schemas.py
scripts/.gitkeep
scripts/README.md
scripts/bootstrap_cloud_src.sh
scripts/deploy_cloud_backend.sh
scripts/templates/cloud_src_README.md.template
scripts/templates/cloud_src_gitignore.template
scripts/test_cloud_backend.sh
```

### 4.2 Historical Documentation / Architecture Planning

These files are historical planning, architecture, capability, or runbook documents. They should be reviewed separately before any future commit.

```text
docs/change_logs/
docs/changes/
docs/plans/
docs/runbooks/cloud-*.md
docs/runbooks/pi-real-device-validation-v1.md
docs/specs/README.md
docs/specs/cloud-storage-repository-v1.md
docs/specs/pi-session-delivery-v1.md
docs/tasks/cloud-convergence-next-steps.md
docs/tasks/cloud-capability-integration-next-steps.md
docs/project-status/cloud-*.md
docs/project-status/pi-*.md
docs/project-status/v2-phase2-result-workbench.md
docs/project-status/v2-phase2.5-polish-plan.md
行为规则.md
```

### 4.3 Runtime Artifacts / Samples / Raw Data / Image Cache

These paths must stay out of Git commits. The current `.gitignore` already excludes the main runtime and sample patterns.

```text
cloud_backend/data/
cloud_backend/sample_data/
cls_*.json
samples/
image/
picture/
*.log
__pycache__/
*.pyc
.env
.env.*
```

### 4.4 Content That Should Not Enter Phase 2.9 By Accident

The following currently untracked scripts and modules are not part of the submitted Phase 2.5-2.8.1 baseline. Do not include them in Phase 2.9 unless they are explicitly reviewed and assigned to the Phase 2.9 auth/role/permission scope.

```text
cloud_backend/dashboard.py
scripts/check_cloud_runtime_observability.sh
scripts/setup_postgres_schema.sh
scripts/upload_real_result.sh
scripts/validate_auth.sh
scripts/validate_cloud_results_center.sh
scripts/validate_postgres.sh
scripts/validate_teacher_api.sh
```

## 5. Phase 2.9 Git Rules

Phase 2.9 must not use:

```bash
git add .
```

Phase 2.9 should only stage explicitly reviewed files related to:

- authentication
- role routing
- permission boundaries
- database schema/migration scripts for auth/roles if explicitly approved
- validation scripts for Phase 2.9 auth/role behavior
- Phase 2.9 specs, tasks, runbooks, and project-status documents

Phase 2.9 must not commit:

- `cloud_backend/data/`
- `cloud_backend/sample_data/`
- `cls_*.json`
- `samples/`
- `image/`
- `picture/`
- logs
- Python caches
- uploaded raw JSON
- sample videos
- screenshots or image caches
- real `.env` or `.env.*` files
- runtime files containing PostgreSQL credentials, JWT secrets, API keys, or passwords

## 6. Recommended Phase 2.9 Commit Workflow

Use explicit staging only:

```bash
git status --short
git add -- <explicit_phase2_9_file_1> <explicit_phase2_9_file_2>
git diff --cached --name-only
git diff --cached --stat
git diff --cached
```

Before committing, confirm:

- staged files are only Phase 2.9 scoped files
- no raw data or runtime artifacts are staged
- no real secrets are staged
- Phase 2.5-2.8.1 accepted files are not accidentally modified unless the change is intentionally part of Phase 2.9
