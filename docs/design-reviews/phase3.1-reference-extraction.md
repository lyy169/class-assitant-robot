# Phase 3.1 Reference Extraction

## Purpose

Extract design elements for the classroom analytics frontend polish stage.

The goal is not to copy any reference page. The goal is to convert useful patterns into the product language of:

```text
智能课堂行为分析与教学反馈平台
```

## Reference Set

Structure reference:

- Ant Design Pro analysis dashboard

Data visualization references:

- IBM Design Language - Charts
- Apache ECharts Examples

Education / AI product references:

- ClickView Classroom Analytics
- Microsoft Teams for Education Insights
- FeedxBoost features page

## Core Decisions

Ant Design Pro should only influence backend structure and density. It should not define the product identity.

The main Phase 3.1 visual identity should be:

```text
Light professional education analytics, with data-rich dashboards and warm teaching-feedback language.
```

## Extracted Patterns

### Data Visualization

Use chart types according to analytic purpose:

- attention/activity timeline -> trend chart
- teaching stage ratios -> part-to-whole chart
- zone performance -> comparison chart
- event distribution -> distribution chart
- risk lessons -> ranking/list view
- recommendations -> insight cards

Use a consistent chart color language:

- attention: blue
- activity: green/cyan
- question/interaction: amber
- risk: red/orange
- neutral: slate/gray

Prefer clearer chart titles and purposeful tooltips over decorative chart complexity.

### Education Product Tone

ClickView shows that classroom analytics should combine evidence and insight:

- video evidence
- engagement curve
- heatmap-like timeline
- student/question/activity sections

Microsoft Education Insights shows that teacher dashboards should lead to actions:

- spotlight cards
- class overview
- next-step prompts
- drill-down paths

FeedxBoost shows that education SaaS can feel light, warm, and productized without becoming a dark monitoring screen.

## Page-Level Direction

### Login

Chinese product entry with clear teacher/admin role demo access.

### Teacher Home

Use teaching insight cards:

- 今日待复盘
- 低专注课堂
- 互动引导不足
- 建议优先查看

### Dashboard Detail

Make `/dashboard` a classroom session analysis page:

- 课堂证据
- 行为趋势
- 互动事件
- 教学建议

### Teacher Trends

Use main trend chart plus risk list and recommendations.

### Teacher Reports

Make reports feel like teaching feedback reports:

- 课堂结论
- 风险原因
- 改进建议
- 数据依据

### Admin Overview / Trends

Show platform health, data ingestion, classroom coverage, and risk distribution with unified visual language.

## Sources

- IBM Design Language Charts: https://www.ibm.com/design/language/data-visualization/charts/
- Apache ECharts Examples: https://echarts.apache.org/examples/en/index.html
- ClickView Classroom Analytics: https://www.clickvieweducation.com/product/classroom-analytics
- Microsoft Education Insights class overview: https://support.microsoft.com/en-us/topic/class-overview-page-in-insights-1386d1b4-3641-4a23-9b9c-0c6c774c2b6c
- FeedxBoost Features: https://feedxboost.com/en/features
