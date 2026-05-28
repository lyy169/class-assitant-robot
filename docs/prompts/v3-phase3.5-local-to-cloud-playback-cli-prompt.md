# CLI Prompt: V3 Phase 3.5c Local-to-Cloud Playback

Use this prompt to prepare scripts and documentation for local-to-cloud classroom video playback validation.

## Working Directory

```text
/root/video_project_src
```

## Goal

Prepare tools that let the operator manually send a local analyzer export package to cloud runtime and verify `/dashboard` video playback.

## Required Files

```text
docs/runbooks/v3-phase3.5-local-to-cloud-playback-runbook.md
docs/project-status/v3-phase3.5-local-to-cloud-playback.md
docs/prompts/v3-phase3.5-local-to-cloud-playback-cli-prompt.md
scripts/phase3_5_send_local_package_to_cloud.sh
scripts/validate_phase3_5_local_to_cloud_playback.sh
```

## Boundaries

- Do not automatically copy from Windows.
- Do not automatically POST JSON during preparation.
- Do not start or restart services.
- Do not modify systemd.
- Do not modify database structure.
- Do not add APIs.
- Do not commit git changes.
- Do not print secrets, tokens, passwords, or full database connection strings.

## Manual Package Staging

The operator must copy:

```text
C:\Users\lyy\Desktop\gradu\phase35_cloud_upload_package\phase35_local_imported_sav_full_classroom_20200908_17
```

to:

```text
/root/video_project_src/cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17
```

## Validation During Preparation

Run only:

```bash
bash -n scripts/phase3_5_send_local_package_to_cloud.sh
bash -n scripts/validate_phase3_5_local_to_cloud_playback.sh
```

Do not run the send script until the package has been manually staged and the operator is ready to POST to cloud.

