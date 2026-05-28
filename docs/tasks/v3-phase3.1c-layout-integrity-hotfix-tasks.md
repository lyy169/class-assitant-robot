# V3 Phase 3.1-c Tasks: Layout Integrity Hotfix

## Task 1: Read Recheck Evidence

Read:

```text
docs/design-reviews/phase3.1b-layout-regression-recheck.md
docs/specs/v3-phase3.1c-layout-integrity-hotfix-spec.md
```

Understand the two confirmed failures:

- `/dashboard`: unreachable bottom caused by classroom result list/table area
- `/admin/trends`: right-side panel/table extends beyond visible viewport

## Task 2: Fix `/dashboard` Scroll Reachability

Problem metric:

```text
scrollHeight=3810
maxBottom=4756
unreachableBottom=true
```

Requirements:

- The result list/table must not extend beyond document scroll height.
- If table is kept, put it in a normal-flow block with stable height.
- Prefer a collapsed secondary section or max-height internal scroll for the result list.
- `.table-scroll` must not cause content to be outside browser-reachable scroll area.
- Debug/raw data must be internally scrollable and must not affect page height incorrectly.

Verify after fix:

```text
/dashboard unreachableBottom=false
```

## Task 3: Fix `/admin/trends` Right Overflow

Problem metric:

```text
clientWidth=1425
maxRight=1724
invisibleRightOverflow=true
```

Requirements:

- The ranking panel/table must remain inside the page container.
- Fix grid column sizing; use `minmax(0, 1fr)` and `min-width: 0` where needed.
- Wrap tables in `.table-scroll` or convert rankings to rank cards/bars.
- Do not rely on global `overflow-x:hidden`.

Verify after fix:

```text
/admin/trends invisibleRightOverflow=false
```

## Task 4: Recheck `/admin/ingestion`

Requirements:

- Recent ingestion records must stay within page container.
- Long IDs/paths should wrap or truncate cleanly.
- Buttons must not become vertical stacks on desktop.
- The page should still scroll to bottom normally.

## Task 5: Tighten Shared CSS

Review `cloud_backend/ui_style.py`.

Rules:

- Avoid global overflow hiding that masks layout defects.
- Keep table overflow local to `.table-scroll`.
- Ensure cards, grids, and panels use `min-width: 0`.
- Ensure content containers use `width: 100%` and do not exceed parent width.
- Ensure details/debug panels use `max-height + overflow:auto` for long content.

## Task 6: Validation Script

Create/update:

```text
scripts/validate_phase3_1c_layout_integrity.sh
```

The script should at least smoke-test acceptance URLs and print manual browser validation instructions if browser automation is unavailable on the Linux server.

If using Playwright is possible, automate the layout check. Otherwise include the console script in the runbook.

## Task 7: Documentation

Create/update:

```text
docs/project-status/v3-phase3.1c-layout-integrity-hotfix.md
docs/runbooks/v3-phase3.1c-layout-integrity-validation-runbook.md
```

Status doc must include:

- before metrics from Phase 3.1-b recheck
- after metrics after this fix
- files changed
- exact fix approach for `/dashboard`
- exact fix approach for `/admin/trends`
- validation result
- remaining risks

## Task 8: Git Discipline

Before staging:

```bash
git status --short
```

Never use:

```bash
git add .
```

Only stage files changed for this hotfix.

Suggested commit:

```text
fix(cloud): repair phase 3.1 dashboard layout integrity
```
