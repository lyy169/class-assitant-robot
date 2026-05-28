# CLI Prompt: V3 Phase 3.5a Cloud Runtime Check Preparation

Use this prompt to prepare the cloud-side runtime check for Phase 3.5 classroom video playback integration.

## Working Directory

```text
/root/video_project_src
```

## Goal

Create documentation and a read-only runtime check script for cloud video playback and local analysis result integration.

## Required Files

```text
docs/specs/v3-phase3.5-cloud-video-playback-integration-spec.md
docs/tasks/v3-phase3.5-cloud-video-playback-integration-tasks.md
docs/runbooks/v3-phase3.5-cloud-runtime-check-runbook.md
docs/project-status/v3-phase3.5-cloud-video-playback-integration.md
scripts/check_phase3_5_cloud_runtime.sh
```

If `docs/prompts` exists, also create:

```text
docs/prompts/v3-phase3.5-cloud-runtime-check-cli-prompt.md
```

## Boundaries

- Do not start services.
- Do not restart services.
- Do not modify systemd.
- Do not modify databases.
- Do not add upload APIs.
- Do not run migrations.
- Do not commit git changes.
- Do not print secrets or full database URLs.

## Validation

Run only:

```bash
bash -n scripts/check_phase3_5_cloud_runtime.sh
```

Do not run deployment commands during this preparation phase.

