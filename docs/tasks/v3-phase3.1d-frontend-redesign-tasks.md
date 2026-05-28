# V3 Phase 3.1d Tasks: Cloud Frontend High-Fidelity Redesign

## Completed / In Progress Scope

- [x] Read Phase 3.1d prompt and design extraction docs.
- [x] Preserve Phase 3.1c layout integrity requirements.
- [x] Extend shared `cloud_backend/ui_style.py` with Phase 3.1d tokens and components.
- [x] Add `/static` mount for optional local login visual asset.
- [x] Redesign `/login` as split-screen education analytics entry.
- [x] Wrap teacher/admin/dashboard content in `.page-main`.
- [x] Rework `/dashboard` first screen into video evidence + teaching insight rail.
- [x] Keep `/dashboard` result table lazy-loaded in collapsed secondary section.
- [x] Convert `/teacher/results` primary list into result cards.
- [x] Strengthen `/teacher/trends` as main chart + right priority rail.
- [x] Keep report center card/report structure and AI optional state.
- [x] Keep `/admin/ingestion` four-step flow board and standardized-video metadata.
- [x] Keep `/admin/trends` ranking as rank cards/progress bars.
- [x] Wrap remaining admin wide tables in `.table-scroll`.
- [x] Add Phase 3.1d validation script.
- [x] Add Phase 3.1d spec, runbook, and status documentation.

## Validation Tasks

- [x] Run static compile in SSHFS workspace.
- [x] Confirm no `overflow-x:hidden` was reintroduced.
- [ ] Start/restart cloud service on Linux server.
- [ ] Run `scripts/validate_phase3_1d_frontend_redesign.sh`.
- [ ] Run browser console layout check on acceptance URLs.
- [ ] Manually review visual hierarchy at 1440x900 and 1366x768.
- [x] Copy the provided login image to `cloud_backend/static/login-education-visual.png`.

## Git Closeout Rules

- Do not use `git add .`.
- Stage only Phase 3.1d frontend files, docs, and script after browser acceptance.
- Do not stage historical dirty files.
- Do not commit before user visual acceptance.
