# Phase 3.1 Frontend Polish Discovery

## 1. Purpose

Prepare the visual direction for Phase 3.1 before implementation.

This discovery uses the currently connected MCP tools:

- filesystem MCP for reading cloud/local/reference files
- Playwright MCP for browser inspection and screenshots

No production code is changed in this discovery step.

## 2. Current Pages Reviewed

Reviewed through the running cloud service:

- `/login`
- `/teacher`
- `/teacher/trends`
- `/teacher/reports`
- `/dashboard`
- `/admin`
- `/admin/trends`

Screenshots captured by Playwright:

- `current-teacher-home.png`
- `current-teacher-trends.png`
- `current-teacher-reports.png`
- `current-admin-trends.png`

## 3. Current Strengths

The platform already has a complete competition demo flow:

- role-aware login exists
- teacher and admin consoles exist
- teacher home is not empty
- trend and report pages exist
- chart and table based analysis exists
- admin overview and ingestion visibility exist
- Phase 2.9 role protection still works; teacher session received 403 when opening admin page

The system is now functionally presentable, but the visual language is still not mature enough for a competition-grade product demo.

## 4. Main Visual Problems

### 4.1 Language and Product Tone Are Mixed

Many visible labels are still English:

- `Teacher Console`
- `Classroom Records`
- `Teaching Trends`
- `Classroom report center`
- `Platform Overview`
- `Apply`
- `Logout`

This weakens the Chinese education product identity.

Phase 3.1 should make primary navigation, hero copy, table labels, filters, buttons, and report text consistently Chinese.

### 4.2 Pages Feel Like Separate Phase Deliverables

The teacher home, dashboard detail page, reports page, trends page, and admin pages share some visual tokens, but they still feel assembled from different development phases.

Specific issues:

- dashboard detail page has a different header structure from teacher/admin consoles
- nav labels and page hierarchy differ across pages
- card spacing and information density are inconsistent
- page introductions are generic and not strongly tied to teaching feedback

Phase 3.1 should introduce a unified shell, unified nav, and shared visual tokens.

### 4.3 Visual Style Is Too Generic Dashboard-Like

The current style uses dark navy header bands, blue gradients, white cards, and large rounded panels. It is clean, but it reads as a generic SaaS dashboard rather than a polished intelligent education platform.

Risk:

- too much dark navy can feel like monitoring/security
- too many large cards make pages long and soft
- charts and report blocks lack storytelling and teaching context

Phase 3.1 should keep professionalism but add an education-oriented product identity.

### 4.4 Competition Demonstration Needs Stronger First-Screen Impact

The first viewport should quickly answer:

- What is this system?
- What classroom is being analyzed?
- What should the teacher/admin pay attention to now?
- What evidence supports the conclusion?

Current first screens show metrics, but the story is weak.

Phase 3.1 should create a stronger first-screen composition:

- role-specific title
- key insight band
- priority indicators
- recent/critical action entry
- concise teaching feedback wording

### 4.5 Chart Presentation Needs More Narrative

Trend charts exist, but they are plain and compact.

Needed improvements:

- clearer chart titles in teaching language
- thresholds or risk hints where useful
- better empty/demo/real data states
- chart cards should explain why the metric matters without adding long instructional text
- avoid clutter while keeping competition visual appeal

### 4.6 Reports Need To Feel Like Teaching Feedback, Not Raw Tables

The report center currently lists lessons and actions. It works, but it does not yet look like a teacher-facing reflection/report product.

Phase 3.1 should improve:

- report list readability
- risk badges
- teaching recommendation layout
- rule report detail structure
- optional AI summary state

## 5. Product Design Direction

Recommended theme:

```text
Professional education analytics + warm teaching feedback + competition-ready data story
```

Avoid:

- dark security monitoring style
- pure data warehouse/admin CRUD feeling
- empty marketing hero
- overdecorated big-screen effect

Use:

- calm light background
- restrained dark header or side navigation
- education-accent colors such as blue, cyan, green, amber
- strong but not noisy metric cards
- compact, readable tables
- chart panels with clear teaching intent
- report cards that read like teaching feedback

## 6. Reference Systems To Learn From

Use these as design references, not direct copies:

- IBM Carbon dashboard and data visualization patterns
- Ant Design Pro dashboard and workbench patterns
- Arco Design Pro analytics layouts
- enterprise education SaaS dashboard patterns
- Figma dashboard/report templates if later available

Reference extraction goals:

- layout rhythm
- data card hierarchy
- filter bar density
- chart panel anatomy
- risk/status badge treatment
- report page structure

## 7. Suggested Phase 3.1 Scope

Cloud-only frontend polish is enough for this stage.

Recommended in scope:

- unified Chinese product naming and navigation labels
- shared teacher/admin shell polish
- login page redesign
- teacher home polish
- teacher trends polish
- teacher reports polish
- dashboard detail polish
- admin overview and admin trends polish
- chart color/token cleanup
- responsive layout check
- Playwright screenshot validation

Out of scope:

- database schema changes
- API contract changes unless required by display bugs
- new auth model
- video transcoding
- local algorithm changes
- Raspberry Pi capture changes
- Figma high-fidelity design import

## 8. Acceptance Direction

Phase 3.1 should be accepted when:

- teacher/admin pages feel like one coherent product
- primary visible text is Chinese and teacher-friendly
- first viewport is more compelling for a competition demo
- reports feel like teaching feedback rather than a raw table
- charts are easier to read and visually consistent
- no Phase 2.9 auth regression
- no Phase 3.0 trend/report API regression
- Playwright screenshots cover teacher/admin desktop views

## 9. Open Decisions For SDD Discussion

Need user confirmation:

1. Should Phase 3.1 prioritize teacher-facing pages first, then admin pages?
2. Should the visual style be light professional, dark tech dashboard, or mixed light + strong dark header?
3. Should all visible UI text become Chinese in this phase?
4. Should `/dashboard` be visually merged into the teacher console shell?
5. Should Figma MCP remain optional for a second polish pass?
