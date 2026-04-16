# Cloud Legacy Boundary

## Mainline Vs Retained Path Vs Legacy

This document clarifies the three boundary levels currently used for the cloud-side project.

## Formal Mainline

Formal mainline means the part that should become the first stable source-managed path.

Current formal mainline:
- `cloud_backend/`

Main responsibilities:
- receive classroom interaction result JSON from the local YOLO workstation
- expose health check
- perform minimal validation
- record logs
- persist raw JSON results

## Retained Path

Retained path means the capability is still a formal business requirement, but the current implementation is not yet the confirmed source-managed mainline.

Current retained path:
- MP4 upload
- video file listing/streaming path
- related `uploads/` runtime directory
- related `backend/` and `frontend/` code paths

Why MP4 upload is still retained:
- Raspberry Pi voice/recording/MP4 upload remains in scope
- the current upload chain is still part of the working project requirement
- removing or forcing migration now would risk breaking online behavior

Why it is not the first source-managed mainline:
- current implementation is mixed with dashboard/demo logic
- coupling between `backend/`, `frontend/`, and deployment runtime data is still high
- it needs a later dedicated convergence decision

## Legacy

Legacy means the capability has exited the formal mainline and should be preserved without being treated as the active architectural center.

Current legacy set:
- root `app.py`
- `templates/`
- `static/`
- `models.py`
- `gunicorn_config.py`
- `README_DEPLOY.md`
- `instance/video.db`

These assets should be preserved first, not deleted.

## How To Understand `frontend/`, `backend/`, and `cloud_backend/`

Current interpretation:

- `cloud_backend/`
  - the new cloud ingestion service
  - formal mainline

- `backend/`
  - partially retained because it still carries MP4-related endpoints
  - partially deferred because it also contains dashboard/demo-oriented API behavior

- `frontend/`
  - currently acts as a UI side of the MP4/dashboard chain
  - retained as a related asset, but not yet confirmed as part of the first source bootstrap

This means:
- `cloud_backend/` should be managed first
- `backend/` and `frontend/` should stay untouched in the deployment copy until their next-step convergence is explicitly decided
- old Flask root assets remain legacy

## Current Operational Rule

For the current stage:

- do not delete legacy assets
- do not cut retained MP4 paths
- do not merge all code paths into one new repo in a single move
- do not treat the current deployment copy as a ready-made clean source repository
