# V3 Phase 3.18 Spec: Demo Trend Visualization Scope

## Goal

Phase 3.18 makes the trend insight pages useful for competition demonstration by explicitly allowing labeled demo trend data on trend pages while keeping real classroom evidence and demo trend evidence separated.

The single-classroom real evidence remains:

```text
phase314_asr_full_classroom_sav_20200908_17
```

Trend visualization demo evidence may use seeded demo records such as:

```text
demo_phase3_001 ... demo_phase3_008
```

## Rationale

Trend insight needs multiple lessons over time. The final real sample is one complete classroom, so it is strong evidence for single-lesson multimodal analysis, but it cannot show long-term trend, ranking, risk-change, or multi-lesson visualization ability by itself.

Therefore:

- Real data proves the analysis chain and final classroom dashboard.
- Demo data demonstrates the platform experience after multiple lessons have accumulated.
- Demo data must be clearly labeled and must not be mixed into the final real sample conclusion.

## Non-Goals

This phase does not:

- Pretend demo trend data is real classroom data.
- Change Phase 3.17 default real-data filtering.
- Put demo records into default real reports.
- Modify core vision or ASR algorithms.
- Modify local analyzer code.
- Modify Raspberry Pi code.
- Re-upload final video.
- Delete database data.
- Commit git changes.

## Demo Trend Data Source

Prefer the existing seed script:

```text
scripts/seed_phase3_demo_trend_data.sh
```

The demo records should be labeled with:

```json
{
  "dataset": {
    "source": "demo",
    "purpose": "phase3_trend_seed"
  },
  "source": {
    "source_kind": "demo"
  }
}
```

If demo data already exists, do not reseed unless validation shows it is missing or stale. If reseeding is needed, use the existing script and do not touch real records.

## Teacher Trend Page Requirements

`/teacher/trends` must support:

- Default `data_source=real` view.
- Explicit `data_source=demo` view.
- Optional `data_source=all` view.

When demo or all data is selected, the page must show a visible note such as:

```text
当前包含演示数据，仅用于比赛展示或功能演示，不代表真实教学趋势。
```

Demo trend view should show at least these visualization abilities when demo data is available:

- Teaching feedback trend line.
- Attention/activity trend line.
- Question/response trend chart.
- Teaching stage structure chart.
- Priority review/risk lessons list.
- Rule-based recommendations.

## Admin Trend Page Requirements

`/admin/trends` must support explicit demo data view and label it. It should show platform-level trend abilities such as:

- Overview metrics.
- Recent trend reports.
- Classroom ranking.
- Teacher activity.
- Risk lessons.

## Separation Requirements

- `/teacher/trends?data_source=real` and `/admin/trends?data_source=real` must not silently include demo records.
- `/teacher/reports` default real-data report center must not become a demo report list.
- Demo records must include labels or quality notes when visible.
- Phase 3.14 final sample remains the real final dashboard sample.
- Phase 3.17 hidden history/test records stay hidden from default real views.

## Suggested Competition Wording

Use this口径 in demo scripts and Q&A:

```text
单堂完整课堂分析使用外部真实 SAV 课堂视频；趋势洞察需要多堂课持续积累，因此使用标注清楚的 demo 数据展示系统在长期使用后的趋势分析和可视化能力。demo 数据不作为真实课堂采集结论。
```

## Acceptance Markers

```text
PHASE318_DEMO_TREND_SEED_SCRIPT_PRESENT=true
PHASE318_TEACHER_TRENDS_DEMO_PAGE_REACHABLE=true
PHASE318_TEACHER_TRENDS_DEMO_WARNING_VISIBLE=true
PHASE318_TEACHER_TRENDS_DEMO_API_OK=true
PHASE318_TEACHER_TRENDS_DEMO_DATA_AVAILABLE=true
PHASE318_TEACHER_TRENDS_DEMO_SERIES_OK=true
PHASE318_TEACHER_TRENDS_DEMO_CHARTS_PRESENT=true
PHASE318_TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT=true
PHASE318_ADMIN_TRENDS_DEMO_API_OK=true
PHASE318_ADMIN_TRENDS_DEMO_SCOPE_OK=true
PHASE318_REAL_TRENDS_SCOPE_STILL_REAL=true
PHASE318_REPORTS_DEFAULT_NOT_DEMO=true
PHASE318_PHASE314_FINAL_SAMPLE_UNCHANGED=true
PHASE318_NO_DEMO_AS_REAL_CLAIM=true
PHASE318_DEMO_TREND_VISUALIZATION_READY=true
```
