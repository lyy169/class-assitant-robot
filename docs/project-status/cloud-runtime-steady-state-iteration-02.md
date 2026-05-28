# Cloud Runtime Steady-State Iteration 02

## 1. Goal

Turn the cloud runtime from an implicit operator choice into an explicit steady-state decision document set without changing APIs, dashboard structure, or storage behavior.

This iteration is limited to:

- documenting foreground vs systemd tradeoffs
- documenting the recommended steady-state choice
- documenting stop/restart guidance
- adding a reusable operator decision template

## 2. Modified Files

- `docs/runbooks/cloud-runtime-and-sqlite-deploy-v1.md`
- `docs/project-status/cloud-steady-state-choice-template.md`
- `docs/project-status/cloud-runtime-steady-state-iteration-02.md`

## 3. Runbook Updates

The deployment runbook now explicitly defines:

- strengths and weaknesses of foreground runtime
- strengths and weaknesses of systemd runtime
- current recommended steady-state choice
- minimum maintenance pattern if foreground continues
- prechecks before moving to systemd
- operator-only systemd adoption steps
- formal stop / restart / restart-after-change guidance

## 4. Template Path

Steady-state choice template:

- `docs/project-status/cloud-steady-state-choice-template.md`

## 5. Current Recommended Steady-State Choice

Current recommendation:

- currently validated runtime baseline:
  - `foreground`
- recommended long-term steady-state mode:
  - `systemd`

Reason:

- foreground mode is already verified and remains the current low-risk fallback
- systemd is the better long-term operating mode for continuous uploads, operator handoff, and restart consistency
- the repo already contains an aligned `.service.example`, so the transition path is documented even though it has not been executed yet

## 6. Operator Actions Still Required

No systemd action has been executed in this iteration.

If the operator decides to stay on foreground:

- keep using `bash scripts/deploy_cloud_backend.sh`
- keep one authoritative runtime session
- rerun observability checks after restart or change

If the operator decides to switch to systemd:

- verify current foreground runtime is green
- copy the `.service.example` into `/etc/systemd/system/`
- run `daemon-reload`
- enable and start the unit
- verify status, logs, and observability checks

## 7. Next-Step Suggestions

1. Record the actual operator choice in `cloud-steady-state-choice-template.md`.
2. If long-term uploads are expected immediately, move to systemd after one final precheck bundle.
3. If foreground is retained temporarily, add one dated operator handoff note for who owns the live terminal session.
