# Cloud Convergence Next Steps

## Round 1 Result Summary

The first round established the following:

- `cloud_backend/` is the confirmed formal cloud mainline for classroom interaction result ingestion
- MP4 upload remains a formal retained requirement
- old Flask login/page/history capabilities are no longer the mainline
- the current `video_project/` directory should stay as the deployment copy
- Git should not be restored directly inside the current deployment directory

Reference documents:
- `docs/plans/cloud-service-boundary.md`
- `docs/plans/cloud-git-convergence-plan.md`

## Round 2 Convergence Direction

Round 2 focuses on preparation, not switching:

- define the blueprint for `video_project_src/`
- clarify what enters the future source repo first
- clarify what stays in the deployment copy for now
- improve `cloud_backend` operational documentation
- prepare for a safe later Git bootstrap

This round does not:
- initialize Git in `video_project/`
- delete legacy assets
- move runtime data
- restart services
- switch the online service path

## First-Batch Source-Managed Assets

The first batch recommended for future `video_project_src/`:

- `cloud_backend/`
- `docs/`
- `scripts/`

These are the smallest stable set that already has clear ownership and low coupling to runtime-only state.

## Assets That Stay As Deployment Copy Or Legacy

Keep in the deployment copy for now:

- `instance/`
- `uploads/`
- `logs/`
- `cloud_backend/data/`

Keep as legacy or deferred:

- old Flask root app: `app.py`
- `templates/`
- `static/`
- `backend/`
- `frontend/`

## Recommended Next Round Decision

It is appropriate in the next round to create `video_project_src/` and initialize Git there only if the following stays true:

- the source directory is created as a separate sibling directory
- the first import scope is limited to `cloud_backend/`, `docs/`, and `scripts/`
- runtime data is explicitly excluded
- no deployment switch is attempted in the same round

## Suggested Round 3 Scope

Recommended scope for the next operational round:

1. Create `video_project_src/`
2. Add initial directory scaffold
3. Copy only the first-batch managed assets
4. Create `.gitignore`
5. Initialize Git inside `video_project_src/`
6. Make the first local bootstrap commit

Not recommended in that same round:

- modifying online service units
- syncing source to deployment automatically
- pulling `backend/` or `frontend/` into the first commit unless separately confirmed
