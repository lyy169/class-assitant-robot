# V3 Phase 3.1-b Status: Dashboard Layout Redesign & Layout Bugfix

## 1. Status

Implemented in SSHFS workspace. Static compile passed locally; runtime and browser layout validation must be executed on the Linux cloud server.

Phase 3.1-a was a foundation pass: it unified Chinese copy, light color tokens, cards, and basic visual language.

Phase 3.1-b is the actual layout-redesign and bugfix pass: it fixes CSS layering, horizontal overflow risk, scroll reachability risk, table squeezing, and reorganizes core pages into dashboard layouts.

## 2. Modified Files

- `cloud_backend/ui_style.py`
- `cloud_backend/teacher_pages.py`
- `cloud_backend/admin_pages.py`
- `cloud_backend/dashboard_v11.py`
- `scripts/validate_phase3_1b_layout.sh`
- `docs/runbooks/v3-phase3.1b-layout-validation-runbook.md`
- `docs/project-status/v3-phase3.1b-dashboard-layout-redesign.md`

## 3. CSS Architecture Changes

- Removed the old duplicated admin global CSS stack and made admin pages use `PHASE31_STYLE`.
- Strengthened `PHASE31_STYLE` as the shared layout layer.
- Added global `box-sizing: border-box`.
- Kept `html/body` scrollable and prevented page-level horizontal overflow.
- Added reusable classes: `app-shell`, `page-main`, `dashboard-grid`, `dashboard-main`, `dashboard-side`, `chart-panel`, `insight-panel`, `evidence-panel`, `report-card`, `action-card`, `table-scroll`, `action-row`, `heat-strip`, `flow-board`, `flow-step`, `progress-track`, and `rank-bar`.
- Added `prefers-reduced-motion` handling.
- Long tables are constrained by `.table-scroll` or card-level horizontal scrolling.

## 4. Page Layout Changes

### `/teacher`

- Rebuilt first screen as teaching feedback summary plus `复盘 Spotlight`.
- Added teaching rhythm strip and action cards.
- Kept recent classroom and classroom overview sections below the first screen.

### `/dashboard`

- Moved classroom result list out of the first screen and into a folded secondary section.
- First screen now focuses on classroom video evidence and teaching feedback.
- Added classroom participation rhythm strip.
- Made attention/activity timeline the main chart.
- Debug/raw data stays collapsed and constrained by max-height.
- Result table uses `table-scroll`; operation buttons remain horizontal.

### `/teacher/trends`

- Reorganized as Ant Design Pro-style main chart plus side review-priority panel.
- Added large teaching feedback trend chart with markLine threshold and markPoint low point.
- Kept secondary charts below: attention/activity, question/response, stage structure, rule recommendations.

### `/teacher/reports`

- Report list uses report cards with risk label, source label, conclusion, suggestion summary, and action row.
- Report detail follows teaching feedback report structure: classroom conclusion, main risks, recommendations, evidence, question/response analysis, and AI status.

### `/admin`

- Status distribution and quick links are localized.
- Platform overview remains compact but uses the shared visual system.

### `/admin/trends`

- Added platform quality trend chart as the main panel.
- Added platform risk strip.
- Kept class and teacher rankings as supporting panels.

### `/admin/ingestion`

- Reworked top area into a four-step flow board:
  树莓派采集 -> 本地分析 -> 云端入库 -> 教师反馈
- Added status lights, data quality progress bar, video availability summary, and recent ingestion cards.
- Removed wide recent-ingestion table squeeze as the primary presentation.

## 5. Layout Bugfixes

- Right-side abnormal blank space is addressed by shared max-width, `width: 100%`, `min-width: 0`, and page-level overflow control.
- Page bottom reachability is addressed by keeping content in normal document flow and avoiding absolute-positioned layout blocks.
- Debug/raw content is constrained by `max-height + overflow:auto`.
- Tables are constrained to scroll within cards instead of expanding document width.
- Action buttons use `action-row` and `white-space: nowrap`.

## 6. Data Visualization Changes

- `/dashboard`: attention/activity timeline uses semantic colors, smooth lines, area fill, Chinese tooltip, and review threshold markLine.
- `/teacher/trends`: main trend chart uses smooth line, area fill, risk threshold, and low-point markPoint.
- `/admin/trends`: platform quality chart added from recent report summaries.
- `/admin/ingestion`: flow board and data-quality progress are non-ECharts lightweight visualizations.
- Heat/rhythm strips added for classroom participation and platform risk rhythm.

## 7. Reference Absorption

- Ant Design Pro: main chart + side ranking, compact metrics, dashboard information density.
- IBM/Carbon/ECharts: semantic chart colors, tooltip/legend localization, chart-purpose mapping, risk threshold lines, empty-state structure.
- ClickView: `/dashboard` combines video evidence, behavior curve, events, and teaching feedback.
- Microsoft Education Insights: teacher home spotlight cards and report conclusion/risk/recommendation structure.
- FeedxBoost: light education-tech tone, warm feedback wording, no dark monitoring style.

## 8. API / Database Boundary

- No database schema changes.
- No upload API changes.
- No permission model changes.
- No new frontend framework.
- No Raspberry Pi or local analyzer changes.

## 9. Validation

Static compile passed:

```text
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
```

Runtime validation script:

```text
scripts/validate_phase3_1b_layout.sh
```

Run:

```bash
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" bash scripts/validate_phase3_1b_layout.sh
```

Runtime result:

```text
pending operator execution on Linux server
```

## 10. Browser Acceptance URLs

- `http://<server>:8011/login`
- `http://<server>:8011/teacher`
- `http://<server>:8011/dashboard`
- `http://<server>:8011/teacher/trends`
- `http://<server>:8011/teacher/reports`
- `http://<server>:8011/teacher/reports?result_id=cls_20260417_101_001`
- `http://<server>:8011/admin`
- `http://<server>:8011/admin/trends`
- `http://<server>:8011/admin/ingestion`

## 11. Residual Risks

- Browser visual acceptance is still required, especially for actual viewport width, scroll height, and chart rendering.
- Some API-provided descriptions may still contain older English wording if backend data itself stores English labels; visible status labels were mapped where pages control rendering.
- Current repository has historical dirty files. Do not use `git add .`.
