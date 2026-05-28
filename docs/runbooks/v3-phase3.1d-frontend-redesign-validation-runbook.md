# V3 Phase 3.1d Runbook: Frontend Redesign Validation

## 1. Start Cloud Service

Run on the Linux cloud server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

If the service is already running, restart it using the project’s normal deployment command.

## 2. Optional Login Image Asset

Phase 3.1d uses this URL when the local asset is available:

```text
/static/login-education-visual.png
```

If the SSHFS editor cannot create `cloud_backend/static`, run on the server:

```bash
cd /root/video_project_src
mkdir -p cloud_backend/static
```

Then copy the provided file from the operator machine or upload it to:

```text
cloud_backend/static/login-education-visual.png
```

The page has a gradient fallback, so the service can start without this image.

## 3. Script Validation

Run:

```bash
cd /root/video_project_src
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" bash scripts/validate_phase3_1d_frontend_redesign.sh
```

Expected markers:

```text
PHASE31D_LOGIN_LAYOUT_OK=true
PHASE31D_TEACHER_LOGIN_OK=true
PHASE31D_TEACHER_HOME_LAYOUT_OK=true
PHASE31D_TEACHER_RESULTS_LAYOUT_OK=true
PHASE31D_DASHBOARD_FIRST_SCREEN_OK=true
PHASE31D_TEACHER_TRENDS_LAYOUT_OK=true
PHASE31D_TEACHER_REPORTS_LAYOUT_OK=true
PHASE31D_ADMIN_LOGIN_OK=true
PHASE31D_ADMIN_HOME_LAYOUT_OK=true
PHASE31D_ADMIN_INGESTION_LAYOUT_OK=true
PHASE31D_ADMIN_TRENDS_LAYOUT_OK=true
PHASE31D_NO_OVERFLOW_GUARD_OK=true
PHASE31D_AUTH_REGRESSION_OK=true
PHASE31D_PHASE30_REGRESSION_OK=true
PHASE31D_REGRESSION_OK=true
```

## 4. Browser Acceptance URLs

Open after logging in:

```text
http://<server>:8011/login
http://<server>:8011/teacher
http://<server>:8011/teacher/results
http://<server>:8011/dashboard
http://<server>:8011/teacher/trends
http://<server>:8011/teacher/reports
http://<server>:8011/teacher/reports?result_id=cls_20260417_101_001
http://<server>:8011/admin
http://<server>:8011/admin/ingestion
http://<server>:8011/admin/trends
```

Recommended desktop viewport:

```text
1440 x 900
1366 x 768
```

## 5. Console Layout Check

Run this in the browser console on each acceptance URL:

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
      right: Math.round(r.right + window.scrollX),
      bottom: Math.round(r.bottom + window.scrollY),
      allowedInternalScroll: isInsideAllowedScroll(el)
    };
  }).filter((x) => Number.isFinite(x.right) && Number.isFinite(x.bottom));
  const visibleRects = rects.filter((x) => !x.allowedInternalScroll);
  const maxRight = Math.max(...visibleRects.map((x) => x.right), 0);
  const maxBottom = Math.max(...visibleRects.map((x) => x.bottom), 0);
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
    topRightOffenders: visibleRects.filter((x) => x.right > de.clientWidth + 2).slice(0, 5),
    bottomOffenders: visibleRects.filter((x) => x.bottom > de.scrollHeight + 50).slice(0, 5)
  };
})();
```

Required:

```text
pageHorizontalOverflow=false
invisibleRightOverflow=false
unreachableBottom=false
```

## 6. Manual Visual Checklist

- `/login` uses split screen with education platform identity and role/demo login actions.
- `/teacher` reads as a teaching feedback workbench, not a generic backend page.
- `/teacher/results` uses scan-friendly classroom cards.
- `/dashboard` first screen shows video evidence + teaching insight + KPI/context, not a results table.
- `/teacher/trends` has a dominant main chart and right review-priority rail.
- `/teacher/reports` reads like a teaching feedback report center.
- `/admin` looks like a platform operation cockpit.
- `/admin/ingestion` clearly shows the four-step three-side data flow.
- `/admin/trends` uses rank cards/progress bars and no squeezed ranking table.
- No obvious right-side blank/cutoff.
- Page can scroll to the real bottom.
- Tables scroll only inside `.table-scroll`.
- Phase 2.9 auth and Phase 3.0 APIs still work.
