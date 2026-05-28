# Cloud Source Copy Manifest

## Purpose

This document defines what should be copied into the future cloud source directory and what must never be copied from the running deployment directory.

## Source Bootstrap Scope

The first source-managed batch is fixed as:
- `cloud_backend/`
- `docs/`
- `scripts/`

These are the only directories that should be copied into the first `video_project_src/` bootstrap.

## Copy Allowlist

Copy these items from the running deployment directory:

- `cloud_backend/`
- `docs/`
- `scripts/`

## Copy Blocklist

Do not copy any of the following:

- `instance/`
- `uploads/`
- `logs/`
- `cloud_backend/data/`
- `.env`
- `.env.*`
- local caches
- bytecode caches
- runtime JSON output
- temporary logs
- ad hoc test output

## Additional Exclusions Inside `cloud_backend/`

Even though `cloud_backend/` is on the allowlist, the following subcontent must be excluded from the copy result:

- `cloud_backend/data/`
- runtime-generated raw JSON
- temporary debug files
- local cache files
- `__pycache__/`
- `*.pyc`
- `*.log`

## Post-Copy Verification

After copying, the source directory must be checked to ensure these are absent:

- `cloud_backend/data/raw/`
- any uploaded media
- any SQLite database file
- any `.env` file
- any runtime log output
- any local cache directory

If such files appear in the source directory, they must be removed from the source directory before Git initialization.
