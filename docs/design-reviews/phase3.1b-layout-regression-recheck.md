# Phase 3.1-b Layout Regression Recheck

## Date

2026-05-04

## Purpose

Recheck the deployed cloud pages after Phase 3.1-b because user reported:

- right-side blank area still exists
- some pages cannot scroll to the real bottom
- some content appears clipped or not fully reachable

## Browser Setup

Viewport used by Playwright:

```text
1440 x 1000
```

Base URL:

```text
http://8.148.205.228:8011
```

## Result Summary

Phase 3.1-b is not ready for final acceptance.

The status document claims that right-side blank space, scroll reachability, and table squeezing were fixed, but browser recheck still found layout failures.

## Evidence

### `/teacher`

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=2207
maxRight=1372
maxBottom=2207
horizontalOverflow=false
unreachableBottom=false
rightWhitespace=53
```

Teacher home is not the main failing page.

### `/dashboard`

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=3810
maxRight=1372
maxBottom=4756
horizontalOverflow=false
unreachableBottom=true
rightWhitespace=53
```

Failure:

```text
maxBottom > scrollHeight + 50
```

Actual elements extend to about `4756px`, but the page scroll height is only `3810px`. This reproduces the user report that the page cannot scroll to the real bottom.

Main offending area:

```text
DIV.table-scroll
TABLE
TBODY
last table rows in classroom result list
```

The result table still sits in a layout that does not correctly contribute to the document scroll height.

### `/teacher/trends`

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=1882
maxRight=1372
maxBottom=1881
horizontalOverflow=false
unreachableBottom=false
rightWhitespace=53
```

No hard scroll failure found in this pass.

### `/teacher/reports`

```text
clientWidth=1440
scrollWidth=1440
scrollHeight=1000
maxRight=1380
maxBottom=928
horizontalOverflow=false
unreachableBottom=false
rightWhitespace=60
```

No hard scroll failure found in this pass.

### `/teacher/reports?result_id=cls_20260417_101_001`

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=2755
maxRight=1372
maxBottom=2756
horizontalOverflow=false
unreachableBottom=false
rightWhitespace=53
```

No hard scroll failure found in this pass.

### `/admin`

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=2609
maxRight=1372
maxBottom=2609
horizontalOverflow=false
unreachableBottom=false
rightWhitespace=53
```

Admin overview is not the main failing page.

### `/admin/trends`

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

Several elements extend to about `1724px`, while the viewport client width is `1425px`. However `scrollWidth` remains `1425px`, so the overflow is not exposed as normal horizontal scrolling. This can create visible right-side blank/cutoff behavior.

Main offending area:

```text
班级表现排行 panel/table
H2
TABLE
THEAD/TR/TH
```

The ranking panel is positioned or sized beyond the visible layout container.

### `/admin/ingestion`

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=4079
maxRight=1372
maxBottom=4079
horizontalOverflow=false
unreachableBottom=false
rightWhitespace=53
```

No hard scroll-height failure in metrics, but screenshot still shows the page feels sparse and several record cards are cramped. Visual polish is still weak.

## Interpretation

The current fix is incomplete.

Likely root causes:

1. The shared CSS added `.table-scroll`, `.dashboard-grid`, and overflow rules, but some page-specific structures still create layout inconsistencies.
2. `/dashboard` still places a long result table in a context where the table content does not fully contribute to document scroll height.
3. `/admin/trends` likely has a grid or card sizing issue where a right-hand panel/table exceeds the viewport but is hidden by `overflow-x: hidden` on `html/body`.
4. Global `overflow-x: hidden` hides horizontal layout bugs instead of fixing them.
5. The layout still uses a centered max-width page with many wide cards, so pages can still feel like old content placed into a new skin instead of a deliberate dashboard composition.

## Required Fixes

### Must Fix `/dashboard`

- Move the long classroom result table out of the main document flow risk area.
- Prefer a collapsed details panel or card/list presentation.
- If table remains, place it in a normal block that contributes to document height.
- `.table-scroll` must not create unreachable bottom.
- Re-run maxBottom vs scrollHeight check after fix.

### Must Fix `/admin/trends`

- Fix the dashboard grid sizing so no element extends beyond `clientWidth`.
- The right-side ranking panel must stay inside the page container.
- Do not hide this with `overflow-x: hidden`; fix the actual grid/card width.
- Re-run maxRight vs clientWidth check after fix.

### Should Improve `/admin/ingestion`

- The page no longer has hard scroll failure in this pass, but visual spacing and card density still look weak.
- Recent ingestion cards need better density and less wasted space.

## Hard Acceptance Checks

Use the browser console on every acceptance URL:

```js
(() => {
  const de = document.documentElement;
  const elements = Array.from(document.querySelectorAll('body *'));
  const maxRight = Math.max(...elements.map(el => el.getBoundingClientRect().right + window.scrollX).filter(Number.isFinite));
  const maxBottom = Math.max(...elements.map(el => el.getBoundingClientRect().bottom + window.scrollY).filter(Number.isFinite));
  return {
    url: location.href,
    clientWidth: de.clientWidth,
    scrollWidth: de.scrollWidth,
    scrollHeight: de.scrollHeight,
    maxRight,
    maxBottom,
    horizontalOverflow: de.scrollWidth > de.clientWidth + 2,
    invisibleRightOverflow: maxRight > de.clientWidth + 2,
    unreachableBottom: maxBottom > de.scrollHeight + 50
  };
})();
```

Required:

```text
horizontalOverflow=false
invisibleRightOverflow=false
unreachableBottom=false
```

If a table intentionally scrolls horizontally, the overflow must be inside `.table-scroll`, not at page level and not hidden by body overflow.
