# V3 Phase 3.1-c Runbook: Layout Integrity Validation

## 1. Start Cloud Service

Run on the Linux cloud server as usual.

Then validate against:

```text
API_BASE_URL=http://127.0.0.1:8011
PUBLIC_BASE_URL=http://8.148.205.228:8011
```

## 2. Script Validation

Run:

```bash
cd /root/video_project_src
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" bash scripts/validate_phase3_1c_layout_integrity.sh
```

Expected markers include:

```text
PHASE31C_DASHBOARD_SCROLL_OK=true
PHASE31C_ADMIN_TRENDS_RIGHT_OVERFLOW_OK=true
PHASE31C_NO_UNREACHABLE_BOTTOM_OK=true
PHASE31C_NO_INVISIBLE_RIGHT_OVERFLOW_OK=true
```

## 3. Browser Layout Validation

Open these URLs in browser after login:

```text
http://8.148.205.228:8011/login
http://8.148.205.228:8011/teacher
http://8.148.205.228:8011/dashboard
http://8.148.205.228:8011/teacher/trends
http://8.148.205.228:8011/teacher/reports
http://8.148.205.228:8011/teacher/reports?result_id=cls_20260417_101_001
http://8.148.205.228:8011/admin
http://8.148.205.228:8011/admin/trends
http://8.148.205.228:8011/admin/ingestion
```

Use desktop viewport around:

```text
1440 x 1000
```

## 4. Console Layout Check

Run this in browser console on each acceptance URL:

```js
(() => {
  const de = document.documentElement;
  const elements = Array.from(document.querySelectorAll('body *'));
  const isInsideAllowedScroll = (el) => Boolean(el.closest('.table-scroll, .debug-scroll, details.debug-details'));
  const rects = elements.map((el) => {
    const r = el.getBoundingClientRect();
    return {
      el,
      tag: el.tagName,
      cls: String(el.className || ''),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80),
      left: Math.round(r.left + window.scrollX),
      right: Math.round(r.right + window.scrollX),
      top: Math.round(r.top + window.scrollY),
      bottom: Math.round(r.bottom + window.scrollY),
      width: Math.round(r.width),
      height: Math.round(r.height),
      allowedInternalScroll: isInsideAllowedScroll(el)
    };
  }).filter((x) => Number.isFinite(x.right) && Number.isFinite(x.bottom));
  const visibleRects = rects.filter((x) => !x.allowedInternalScroll);
  const maxRight = Math.max(...visibleRects.map((x) => x.right), 0);
  const maxBottom = Math.max(...visibleRects.map((x) => x.bottom), 0);
  const tableScrollContainers = Array.from(document.querySelectorAll('.table-scroll')).map((el) => {
    const r = el.getBoundingClientRect();
    return {
      left: Math.round(r.left + window.scrollX),
      right: Math.round(r.right + window.scrollX),
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      internalHorizontalScroll: el.scrollWidth > el.clientWidth + 2,
      containerBeyondViewport: r.right > de.clientWidth + 2
    };
  });
  return {
    url: location.href,
    clientWidth: de.clientWidth,
    scrollWidth: de.scrollWidth,
    scrollHeight: de.scrollHeight,
    maxRight,
    maxBottom,
    pageHorizontalOverflow: de.scrollWidth > de.clientWidth + 2,
    invisibleRightOverflow: maxRight > de.clientWidth + 2,
    unreachableBottom: maxBottom > de.scrollHeight + 50,
    tableScrollContainers,
    topRightOffenders: visibleRects.filter((x) => x.right > de.clientWidth + 2).sort((a, b) => b.right - a.right).slice(0, 5).map(({el, ...x}) => x),
    bottomOffenders: visibleRects.filter((x) => x.bottom > de.scrollHeight + 50).sort((a, b) => b.bottom - a.bottom).slice(0, 5).map(({el, ...x}) => x)
  };
})();
```

Required:

```text
pageHorizontalOverflow=false
invisibleRightOverflow=false
unreachableBottom=false
```

Exception:

Wide table contents may scroll inside `.table-scroll`, but the `.table-scroll` container itself must not exceed the viewport.

## 5. Visual Checks

### `/dashboard`

Pass only if:

- page scrolls to real bottom
- classroom result list does not disappear below reachable scroll height
- long table/list is in stable normal flow or internally scrollable
- debug/raw data does not break page height

### `/admin/trends`

Pass only if:

- no ranking panel/table is cut off to the right
- right-side chart/ranking panels remain inside page container
- no hidden horizontal layout bug remains

### `/admin/ingestion`

Pass only if:

- record cards stay inside page width
- operation buttons remain readable
- page reaches bottom normally

## 6. Status Document

After validation, update:

```text
docs/project-status/v3-phase3.1c-layout-integrity-hotfix.md
```

Include actual before/after metrics for `/dashboard` and `/admin/trends`.
