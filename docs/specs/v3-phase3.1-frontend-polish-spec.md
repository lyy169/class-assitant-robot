# V3 Phase 3.1 Spec: Frontend Dashboard Polish

## 1. Goal

Upgrade the cloud frontend from staged functional pages to a competition-ready intelligent classroom teaching feedback dashboard system.

Primary direction:

```text
Chinese education product tone
light professional data platform
teacher-first classroom evidence and feedback story
unified teacher/admin visual shell
readable charts and clear empty states
```

## 2. Page Scope

Teacher-facing:

- `/login`
- `/teacher`
- `/teacher/results`
- `/dashboard`
- `/teacher/trends`
- `/teacher/reports`

Admin-facing:

- `/admin`
- `/admin/classrooms`
- `/admin/teachers`
- `/admin/results`
- `/admin/ingestion`
- `/admin/trends`

## 3. Reference Sources

References are used as pattern input, not copied designs:

- Ant Design Pro: shell, navigation, metric density, dashboard/table structure.
- IBM Design Language and ECharts: chart purpose, tooltip, legend, color semantics.
- ClickView Classroom Analytics: video evidence + engagement curve + event explanation.
- Microsoft Education Insights: action cards, risk attention, teacher next steps.
- FeedxBoost: warm, light, education-product tone.

## 4. Visual Principles

- Primary visible UI text should be Chinese.
- Use a shared visual token layer for colors, cards, buttons, badges, filters, empty states, and chart containers.
- Keep the interface light and education-oriented, not a dark monitoring screen.
- Charts should explain teaching questions: time trend, composition, comparison, priority.
- Risk and data-source states must be visually explicit.

Color semantics:

- 专注度 / attention: blue
- 活跃度 / activity: green/cyan
- 提问互动 / question: amber
- 风险 / risk: orange/red
- 辅助 / neutral: slate/gray

## 5. Data And API Boundary

No database schema changes.

No upload API changes.

No permission model changes.

No Raspberry Pi or local analyzer changes.

Existing Phase 2.9 auth and Phase 3.0 trend/report APIs must remain compatible.

## 6. Forbidden Scope

- No new frontend framework.
- No PDF/Excel export.
- No video transcoding/upload redesign.
- No raw JSON structure changes.
- No Figma MCP.
- No `git add .`.
- No historical dirty file sweep.

## 7. Acceptance Criteria

Pass when:

- `/login` looks like a Chinese intelligent education platform entry.
- Teacher and admin pages share a coherent shell and visual system.
- `/dashboard` is presented as single-classroom evidence and teaching feedback dashboard.
- Teacher trends and reports read as teaching insight/report pages, not raw tables.
- Admin overview/trends/ingestion follow the same product style.
- Charts stay readable and do not collapse on empty data.
- Video missing and AI unconfigured states are friendly.
- Phase 2.9 auth and Phase 3.0 trend/report regressions pass.

## 8. Git Rule

Only explicitly stage Phase 3.1 related files. Never use:

```bash
git add .
```
