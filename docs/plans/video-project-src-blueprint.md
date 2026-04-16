# Video Project Src Blueprint

## Purpose

This document defines the target blueprint for the future `video_project_src/` source repository.

The goal is to prepare a clean source tree for Git management without modifying the current running deployment copy at `video_project/`.

## Core Principle

- `video_project/` remains the running deployment copy
- `video_project_src/` will be the future source-of-truth workspace
- runtime data stays in the deployment copy
- legacy assets are documented before any later isolation work

## Proposed Top-Level Layout

Recommended structure for the future source directory:

```text
video_project_src/
├── cloud_backend/
├── docs/
├── scripts/
├── legacy/
├── .gitignore
└── README.md
```

Alternative naming such as `cloud-backend/` is possible, but keeping `cloud_backend/` is recommended for consistency with the current import path and service examples.

## First-Batch Managed Assets

The first batch that should enter the source repository:

- `cloud_backend/`
- `docs/`
- `scripts/`

Reasoning:
- `cloud_backend/` is the confirmed cloud mainline
- `docs/` already contains boundary, convergence, and operational decisions
- `scripts/` is needed for future sync, verification, and deployment helpers

## Deferred Assets

The following should be deferred from the first bootstrap of `video_project_src/`:

- `backend/`
- `frontend/`
- root-level old Flask entry `app.py`
- `templates/`
- `static/`
- `instance/`
- `uploads/`
- `logs/`
- `cloud_backend/data/`

## Why These Are Deferred

### Deferred but may later be managed

- `backend/`
  - contains MP4-related API paths that are still formally retained
  - also contains dashboard/demo-oriented logic that is not the current cloud mainline
- `frontend/`
  - currently couples to the MP4 and dashboard path
  - should not be pulled into the first clean bootstrap until its role is confirmed

### Deferred as legacy

- `app.py`
- `templates/`
- `static/`

These belong to the older Flask application path and should only be moved under a later `legacy/` strategy after the new source repo is stable.

### Deferred as runtime-only data

- `instance/`
- `uploads/`
- `logs/`
- `cloud_backend/data/`

These are deployment/runtime assets and must not be treated as source-controlled content.

## Planned Role Of `legacy/`

The future `legacy/` directory in `video_project_src/` is a documentation-first boundary, not an immediate copy target.

Initial use:
- hold migration notes
- hold boundary documentation
- hold future manifests of retained old assets

Not for the current round:
- copying old Flask runtime files into the new repo
- moving live databases
- moving uploads
- moving online configs

## Recommended Bootstrap Order

1. Create `video_project_src/` as a separate directory
2. Initialize Git only inside `video_project_src/`
3. Add `cloud_backend/`, `docs/`, and `scripts/`
4. Add `.gitignore` before the first commit
5. Add README and source/deploy boundary notes
6. Keep deployment sync as a later step
