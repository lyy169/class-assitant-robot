# V3 Phase 3.1-c Status: Layout Integrity Hotfix

## 1. Status

Implemented in SSHFS workspace. Static compile passed locally. Runtime HTTP validation and browser console layout validation must be executed on the Linux cloud server.

This phase is intentionally narrow. It does not continue visual redesign; it only fixes layout integrity failures confirmed after Phase 3.1-b.

## 2. Before Metrics

From `docs/design-reviews/phase3.1b-layout-regression-recheck.md`.

### `/dashboard`

```text
clientWidth=1425
scrollWidth=1425
scrollHeight=3810
maxRight=1372
maxBottom=4756
horizontalOverflow=false
unreachableBottom=true
```

Root cause:

```text
DIV.table-scroll / TABLE / TBODY / classroom result list rows
```

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

Root cause:

```text
班级表现排行 panel/table
```

## 3. Files Changed

- `cloud_backend/ui_style.py`
- `cloud_backend/dashboard_v11.py`
- `cloud_backend/admin_pages.py`
- `scripts/validate_phase3_1c_layout_integrity.sh`
- `docs/project-status/v3-phase3.1c-layout-integrity-hotfix.md`

## 4. Fix Approach

### `/dashboard`

- Removed the always-present classroom result table from the visible DOM path.
- Added `dashboard-results-template` and `dashboard-results-mount`.
- The result table is injected only when the result-list `<details>` section is opened.
- This prevents hidden/collapsed result table rows from being counted as unreachable bottom content.
- Debug/raw data remains collapsed and internally scrollable.

### `/admin/trends`

- Replaced the right-side class ranking table with `rankCards()` output using `.rank-bar` and `.record`.
- Wrapped remaining admin trend tables in `.table-scroll`.
- This prevents wide table minimum widths from forcing the right ranking panel beyond viewport width.

### Shared CSS

- Removed global `overflow-x: hidden` from `html` and `body`.
- Kept overflow local to `.table-scroll`.
- Preserved `min-width: 0`, `width: 100%`, and grid constraints so actual overflow is visible to validation instead of hidden.

## 5. Validation

Static compile passed:

```text
python -m py_compile cloud_backend/ui_style.py cloud_backend/dashboard_v11.py cloud_backend/admin_pages.py cloud_backend/teacher_pages.py cloud_backend/login_pages.py
```

Runtime script:

```text
scripts/validate_phase3_1c_layout_integrity.sh
```

Run:

```bash
cd /root/video_project_src
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" bash scripts/validate_phase3_1c_layout_integrity.sh
```

Runtime result:

```text
pending operator execution on Linux server
```

Browser console validation:

```text
pending operator execution with the script in docs/runbooks/v3-phase3.1c-layout-integrity-validation-runbook.md
```

Required after metrics:

```text
/dashboard unreachableBottom=false
/admin/trends invisibleRightOverflow=false
all acceptance URLs pageHorizontalOverflow=false unless overflow is inside .table-scroll
```

## 6. Browser Acceptance URLs

- `http://<server>:8011/login`
- `http://<server>:8011/teacher`
- `http://<server>:8011/dashboard`
- `http://<server>:8011/teacher/trends`
- `http://<server>:8011/teacher/reports`
- `http://<server>:8011/teacher/reports?result_id=cls_20260417_101_001`
- `http://<server>:8011/admin`
- `http://<server>:8011/admin/trends`
- `http://<server>:8011/admin/ingestion`

## 7. Remaining Risks

- The final pass depends on real browser metrics after deploying/restarting the cloud service.
- If API data contains extremely long unbroken values, they should still wrap because shared cards use `overflow-wrap:anywhere`; browser validation should confirm.
- Repository still contains historical dirty files. Do not use `git add .`.
