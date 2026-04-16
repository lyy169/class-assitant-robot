# Cloud Src Bootstrap Checklist

## Goal

This checklist defines what must be confirmed before creating the future `video_project_src/` source directory and initializing Git there.

## Before Creating `video_project_src/`

Confirm all of the following:

- the current `video_project/` directory remains the running deployment copy
- no Git initialization will happen inside `video_project/`
- the first import scope is limited to `cloud_backend/`, `docs/`, and `scripts/`
- no runtime directories will be moved during bootstrap
- no online service switch is bundled into the Git bootstrap round

## Directories That Must Not Be Copied Blindly

These must not be copied wholesale into the first source repo bootstrap:

- `instance/`
- `uploads/`
- `logs/`
- `cloud_backend/data/`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`

These are runtime, cache, or build-output paths rather than source-of-truth code.

## Runtime Data That Must Not Enter Git

Do not place the following into Git:

- SQLite database files such as `instance/video.db`
- uploaded MP4 or other media files in `uploads/`
- runtime logs in `logs/`
- raw result JSON in `cloud_backend/data/raw/`
- local caches and Python bytecode
- local `.env` files and secrets

## First `.gitignore` Coverage

The first `.gitignore` in `video_project_src/` should cover at least:

- `.env`
- `.env.*`
- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.mypy_cache/`
- `.venv/`
- `venv/`
- `logs/`
- `uploads/`
- `instance/`
- `cloud_backend/data/`
- `node_modules/`
- `dist/`

## What The First Commit Should Include

The first commit should contain only the clean bootstrap set:

- `cloud_backend/`
- `docs/`
- `scripts/`
- root `README.md`
- root `.gitignore`
- source/deploy boundary documentation

It should not include:

- deployment-only runtime files
- online service state
- copied databases
- uploaded files
- legacy Flask runtime assets unless explicitly added as documentation-only references

## Safety Check Before Git Init

Immediately before `git init` inside `video_project_src/`, confirm:

- the working path is the new source directory, not `video_project/`
- the file tree contains only first-batch managed assets
- `.gitignore` already exists
- no secrets or runtime artifacts have been copied in

## Recommended Bootstrap Outcome

If all items above are satisfied, then the next round is suitable for:

1. creating `video_project_src/`
2. copying only the first-batch managed assets
3. initializing Git in that new directory
4. making the first local bootstrap commit
