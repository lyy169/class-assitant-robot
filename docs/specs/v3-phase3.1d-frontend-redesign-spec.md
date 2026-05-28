# V3 Phase 3.1d Spec: Cloud Frontend High-Fidelity Redesign

## Goal

Phase 3.1d upgrades the cloud frontend from a staged backend-like interface into a competition-friendly intelligent classroom teaching feedback platform.

This is a layout and visual hierarchy redesign, not a database/API feature phase.

## Scope

Pages in scope:

- `/login`
- `/teacher`
- `/teacher/results`
- `/dashboard`
- `/teacher/trends`
- `/teacher/reports`
- `/admin`
- `/admin/ingestion`
- `/admin/trends`

Allowed changes:

- Shared HTML/CSS layout tokens.
- Server-rendered page structure.
- ECharts options and chart container hierarchy.
- Lightweight local static asset path for the login visual panel.
- Validation script and documentation.

Forbidden changes:

- No database schema changes.
- No upload API changes.
- No raw JSON changes.
- No auth/role/permission model changes.
- No Raspberry Pi or local analyzer changes.
- No React/Vue/Vite/Tailwind migration.
- No `git add .`.

## Design Direction

Visual direction:

```text
Light professional education analytics platform
+ data-rich dashboard canvas
+ warm teaching feedback language
+ competition demonstration quality
```

Core layout:

```text
left sidebar 240px
+ top/context page header
+ KPI row
+ main chart or evidence area
+ right insight rail
+ secondary cards/tables constrained by local scroll containers
```

Key tokens:

- Background: `#F5F7FB`.
- Surface: `#FFFFFF`.
- Border: `#DDE5F0`.
- Text: `#102033`.
- Primary/attention: `#2563EB`.
- Activity: `#14B8A6`.
- Teaching accent: `#7C3AED`.
- Interaction/warning: `#F59E0B`.
- Risk: `#EF4444`.

## Page Requirements

### `/login`

- Split-screen layout.
- Left: product name, three-side pipeline, role cards, real login form, demo login buttons.
- Right: education analytics visual panel using `/static/login-education-visual.png` when available, with gradient fallback.
- Demo buttons must call `/api/auth/login`.

### `/teacher`

- Teacher workbench layout.
- KPI cards.
- Main teaching feedback summary.
- Right-side review spotlight.
- Recent classroom cards and teaching rhythm strip.

### `/teacher/results`

- Classroom result cards are primary.
- Each card includes lesson, classroom, status, score, video availability, and actions.
- Avoid wide table squeeze for small result sets.

### `/dashboard`

- First screen must prioritize video evidence and teaching insight.
- Left: classroom video evidence panel.
- Right: teaching insight rail with score, summary, status actions, and key events.
- Main attention/activity timeline remains the visual anchor.
- Result list remains secondary and lazy-loaded in a collapsed section.
- Debug/raw data remains collapsed and internally scrollable.

### `/teacher/trends`

- KPI row.
- Main trend chart + right review-priority rail.
- Secondary charts for attention/activity, question/response, stage distribution.
- Default `data_source=real`.

### `/teacher/reports`

- Report cards and teaching feedback detail structure.
- AI summary is optional and must not block rule reports.

### `/admin`

- Platform cockpit style with pipeline, metrics, latest results, status distribution, and quick links.

### `/admin/ingestion`

- Four-step ingestion flow board:
  树莓派采集 -> 本地分析 -> 云端入库 -> 教师反馈.
- Preserve standardized video metadata display.
- Device/status table remains in `.table-scroll`.

### `/admin/trends`

- Platform trend main chart.
- Ranking uses rank cards/progress bars, not wide ranking tables.

## Layout Integrity

Phase 3.1d must preserve Phase 3.1c layout integrity:

- No page-level `overflow-x:hidden` as a hidden fix.
- No invisible right overflow.
- No unreachable bottom.
- Tables must be inside `.table-scroll`.
- Debug/raw content must be collapsed or internally scrollable.
- Responsive layouts must use `min-width:0`.

## Acceptance

Pass requires:

- Static Python compile passes.
- Runtime validation script passes.
- Browser console layout metrics pass.
- Manual visual review confirms pages are structurally different from Phase 3.1-a/b.
- API/database/raw JSON remain unchanged.
