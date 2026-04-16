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
- Use `test_cloud_backend.sh` only for smoke verification of the ingestion endpoint.
- Keep service-install or service-enable actions separate from test scripts.
- Prefer `.service.example` or documentation updates before any real process-manager change.

Naming suggestions:
- `test_*.sh` for validation and smoke tests
- `debug_*.sh` for diagnostics
- `deploy_*.sh` for deployment helpers
