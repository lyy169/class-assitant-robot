# V3 Phase 3.1-b Runbook: Dashboard Layout Validation

## 1. Start Cloud Service

Run on the Linux cloud server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Expected:

```text
CLOUD_DB_BACKEND=postgres
Uvicorn running on http://0.0.0.0:8011
```

## 2. Automated Validation

Run in another terminal:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" bash scripts/validate_phase3_1b_layout.sh
```

Expected markers:

```text
PHASE31B_LOGIN_OK=true
PHASE31B_TEACHER_HOME_LAYOUT_OK=true
PHASE31B_DASHBOARD_LAYOUT_OK=true
PHASE31B_DASHBOARD_SCROLL_OK=true
PHASE31B_TEACHER_TRENDS_LAYOUT_OK=true
PHASE31B_TEACHER_REPORTS_LAYOUT_OK=true
PHASE31B_ADMIN_HOME_LAYOUT_OK=true
PHASE31B_ADMIN_TRENDS_LAYOUT_OK=true
PHASE31B_ADMIN_INGESTION_LAYOUT_OK=true
PHASE31B_NO_PAGE_OVERFLOW_OK=true
PHASE31B_NO_UNREACHABLE_BOTTOM_OK=true
PHASE31B_TEXT_LOCALIZATION_OK=true
PHASE31B_EDUCATION_STYLE_OK=true
PHASE31B_CHART_VISUAL_POLISH_OK=true
PHASE31B_VISUAL_EMPTY_SPACE_OK=true
PHASE31B_MOTION_SAFE_OK=true
PHASE31B_REFERENCE_ABSORPTION_VISIBLE=true
PHASE31B_AUTH_REGRESSION_OK=true
PHASE31B_PHASE30_REGRESSION_OK=true
PHASE31B_REGRESSION_OK=true
```

## 3. Browser Acceptance URLs

Open:

```text
http://<server>:8011/login
http://<server>:8011/teacher
http://<server>:8011/dashboard
http://<server>:8011/teacher/trends
http://<server>:8011/teacher/reports
http://<server>:8011/teacher/reports?result_id=cls_20260417_101_001
http://<server>:8011/admin
http://<server>:8011/admin/trends
http://<server>:8011/admin/ingestion
```

## 4. Layout Console Check

Run this in DevTools Console on each core page:

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
    clientHeight: de.clientHeight,
    scrollHeight: de.scrollHeight,
    maxRight,
    maxBottom,
    horizontalOverflow: de.scrollWidth > de.clientWidth + 2,
    unreachableBottom: maxBottom > de.scrollHeight + 50
  };
})();
```

Acceptance:

- `horizontalOverflow` should be `false`.
- If a table is wide, horizontal scrolling must be inside `.table-scroll` or a card, not the whole page.
- `unreachableBottom` must be `false`.
- `window.scrollTo(0, document.body.scrollHeight)` should reach the actual bottom content.

## 5. Manual Visual Checklist

- `/dashboard` first screen emphasizes classroom evidence and teaching feedback, not the result table.
- `/dashboard` result list is secondary and folded under the analysis.
- `/teacher/trends` has a main trend chart plus a review-priority side panel.
- `/admin/ingestion` has a four-step ingestion flow board and recent ingestion cards.
- Long tables do not squeeze action buttons vertically.
- Main status values are Chinese: 待复盘, 已复盘, 已归档, 高风险, 中风险, 低风险, 真实数据, 演示数据.
- Motion is subtle and disabled under `prefers-reduced-motion`.
