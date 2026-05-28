# Scripts

This folder stores helper scripts that should be run on the remote Linux server.

Notes:
- The project is edited through `sshfs`.
- Local execution may not match the real server environment.
- Linux-specific install, service, and verification steps should be added here as standalone scripts.
- After you run a script on the server, send back the output so we can continue safely.

Current boundary:
- `deploy_cloud_backend.sh` and `test_cloud_backend.sh` are for the new `cloud_backend/` service path.
- Do not use this folder to directly rewrite or reset the current deployment directory.
- Future sync/deploy scripts should treat the current `video_project/` as a deployment copy and keep runtime assets intact.
- Runtime assets that must not be overwritten by default include `uploads/`, `instance/`, `logs/`, and `cloud_backend/data/`.

Future sync expectations:
- Add source-to-deploy sync scripts only after `video_project_src/` exists.
- Sync scripts should use an explicit allowlist such as `cloud_backend/`, `docs/`, and `scripts/`.
- Sync scripts should exclude runtime state, `.env`, uploaded media, databases, logs, caches, and build artifacts by default.
- Sync scripts should print the planned file set before any copy/update step.

Cloud backend operations:
- `deploy_cloud_backend.sh` is the current source-side manual startup helper for `/root/video_project_src`.
- It expects the server-side runtime env file at `cloud_backend/.env.runtime` and the formal source-side port `8011`.
- `check_cloud_runtime_observability.sh` is the minimal operator observability script for continuous-upload monitoring.
- It checks the SQLite file, recent raw files, recent API output, and dashboard HTML markers without changing service state.
- `upload_real_result.sh` is the current V1.1 upload validation helper against `POST /api/interaction-results`.
- `test_cloud_backend.sh` is a historical smoke script and should not be treated as the formal V1.1 validation path.
- Keep service-install or service-enable actions separate from validation scripts.
- Prefer `.service.example` or documentation updates before any real process-manager change.

Naming suggestions:
- `test_*.sh` for validation and smoke tests
- `debug_*.sh` for diagnostics
- `deploy_*.sh` for deployment helpers
