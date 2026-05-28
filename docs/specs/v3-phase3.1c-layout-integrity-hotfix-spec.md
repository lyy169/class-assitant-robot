# V3 Phase 3.1-c Spec: Layout Integrity Hotfix

## 1. Purpose

Phase 3.1-b still fails browser layout acceptance.

This phase is a narrow hotfix focused on layout correctness, not visual redesign.

The goal is to make the cloud frontend structurally reliable before any further education-style or Figma-driven visual work.

## 2. Background

User reported after Phase 3.1-b:

- right-side blank / cutoff still exists
- some pages cannot scroll to the real bottom
- some content appears clipped or not fully visible

Browser recheck confirmed hard failures.

Detailed evidence is recorded in:

```text
docs/design-reviews/phase3.1b-layout-regression-recheck.md
```

## 3. Confirmed Failures

### `/dashboard`

Measured at 1440 x 1000 viewport:

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=3810
maxRight=1372
maxBottom=4756
horizontalOverflow=false
unreachableBottom=true
```

Failure:

```text
maxBottom > scrollHeight + 50
```

Main offending area:

```text
DIV.table-scroll
TABLE
TBODY
classroom result list rows
```

The page contains content below the browser-recognized scroll height.

### `/admin/trends`

Measured at 1440 x 1000 viewport:

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=1864
maxRight=1724
maxBottom=1864
horizontalOverflow=false
unreachableBottom=false
rightWhitespace=-299
```

Failure:

```text
maxRight > clientWidth + 2
```

Main offending area:

```text
班级表现排行 panel/table
```

Elements extend beyond the viewport, but page-level horizontal scroll is hidden or not exposed.

## 4. Scope

In scope:

- fix `/dashboard` unreachable bottom
- fix `/admin/trends` invisible right overflow
- check `/admin/ingestion` for layout density and internal scrolling
- update shared layout CSS only as needed
- update validation script to fail on layout integrity violations
- update project status docs with actual browser metrics

Out of scope:

- no new visual redesign
- no new animation work
- no Figma integration
- no database changes
- no API contract changes
- no upload pipeline changes
- no Raspberry Pi changes
- no local analyzer changes

## 5. Hard Requirements

### 5.1 Do Not Hide Bugs

Do not use global `overflow-x: hidden` as the fix.

If page-level horizontal overflow exists, find and fix the offending grid/card/table width.

Allowed:

- `.table-scroll { overflow-x: auto; }` for intentionally wide tables
- clipping only within a local table container

Not allowed:

- hiding page-level overflow while elements still extend beyond the viewport

### 5.2 Layout Integrity Metrics

For all acceptance pages:

```text
/login
/teacher
/dashboard
/teacher/trends
/teacher/reports
/teacher/reports?result_id=cls_20260417_101_001
/admin
/admin/trends
/admin/ingestion
```

Required:

```text
unreachableBottom=false
invisibleRightOverflow=false
```

Where:

- `unreachableBottom` means non-table-scroll visible content extends past `documentElement.scrollHeight + 50`.
- `invisibleRightOverflow` means non-table-scroll visible content extends past `documentElement.clientWidth + 2`.

Wide table descendants inside `.table-scroll` may exceed the viewport only if the `.table-scroll` container itself is inside the viewport and has internal horizontal scrolling.

### 5.3 `/dashboard`

The classroom result list must not create unreachable bottom.

Acceptable fixes:

- move result list into a collapsed `<details>` section with stable normal-flow height
- replace the long table with compact cards
- constrain the table section with `max-height` and internal `overflow:auto`
- keep the `.table-scroll` container itself in normal flow and fully counted by document height

Debug/raw data must remain collapsed and internally scrollable.

### 5.4 `/admin/trends`

The right-side ranking panel must not extend beyond the page container.

Acceptable fixes:

- fix dashboard grid columns
- use `minmax(0, 1fr)` correctly
- make panel/card `min-width: 0`
- wrap tables in `.table-scroll`
- convert ranking tables to cards or rank bars

### 5.5 `/admin/ingestion`

No hard failure was found in the last metric pass, but the page remains visually dense and record cards can feel cramped.

Minimum fix:

- ensure every record card stays inside the page container
- ensure action buttons do not stack vertically unless on mobile
- ensure long IDs/paths wrap or are truncated cleanly

## 6. Validation Script

Create or update:

```text
scripts/validate_phase3_1c_layout_integrity.sh
```

The script may use HTTP smoke checks plus a browser-console/manual validation runbook. If Playwright is available in the server environment, automate browser checks. If not, provide copy-paste JS in the runbook.

Expected markers:

```text
PHASE31C_LOGIN_OK=true
PHASE31C_TEACHER_HOME_LAYOUT_OK=true
PHASE31C_DASHBOARD_LAYOUT_OK=true
PHASE31C_DASHBOARD_SCROLL_OK=true
PHASE31C_TEACHER_TRENDS_LAYOUT_OK=true
PHASE31C_TEACHER_REPORTS_LAYOUT_OK=true
PHASE31C_ADMIN_HOME_LAYOUT_OK=true
PHASE31C_ADMIN_TRENDS_LAYOUT_OK=true
PHASE31C_ADMIN_TRENDS_RIGHT_OVERFLOW_OK=true
PHASE31C_ADMIN_INGESTION_LAYOUT_OK=true
PHASE31C_NO_UNREACHABLE_BOTTOM_OK=true
PHASE31C_NO_INVISIBLE_RIGHT_OVERFLOW_OK=true
PHASE31C_AUTH_REGRESSION_OK=true
PHASE31C_PHASE30_REGRESSION_OK=true
```

## 7. Acceptance

This phase passes only when:

- `/dashboard` no longer has unreachable bottom
- `/admin/trends` no longer has invisible right overflow
- all acceptance URLs pass layout integrity checks
- long tables are either internally scrollable or converted to stable card/list layouts
- status document records actual browser metrics after fix

Do not mark this phase complete based only on static compile.
