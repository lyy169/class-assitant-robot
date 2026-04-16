# Video Project Cloud Source

## Purpose

This directory is the formal cloud-side source repository for `video_project`.

It exists to provide a Git-managed source baseline without directly converting the running deployment copy into a repository.

## Currently Managed Scope

The current managed scope is limited to:
- `cloud_backend/`
- `docs/`
- `scripts/`

## Currently Unmanaged Scope

The following are intentionally not managed in this first bootstrap:
- `backend/`
- `frontend/`
- root old Flask app and related legacy assets
- `instance/`
- `uploads/`
- `logs/`
- `cloud_backend/data/`

## Relationship To The Running Directory

The running deployment directory remains separate:

```text
/root/video_project
```

This source directory is not the live running directory.

Its purpose is to:
- manage source changes safely
- keep runtime state out of Git
- support later reviewable deployment sync

## Development Principles

- do not treat runtime data as source code
- do not mix online deployment changes with source bootstrap changes
- keep `cloud_backend/` as the confirmed cloud formal mainline
- retain legacy assets separately until an explicit isolation round is executed
