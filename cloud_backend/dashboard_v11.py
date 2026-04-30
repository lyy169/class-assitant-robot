"""Dashboard helpers aligned to classroom feedback JSON schema V1.1."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from .repository_interface import ResultRepository


def latest_result_or_404(
    repository: ResultRepository,
    classroom_id: Optional[str] = None,
) -> tuple[dict[str, Any], Path, str]:
    latest_result = repository.latest_result(classroom_id=classroom_id)
    if latest_result is None:
        raise HTTPException(status_code=404, detail="No classroom interaction result is available yet")
    return latest_result


def build_results_center_html(
    latest_payload: dict[str, Any],
    latest_source_path: Path,
    latest_source_kind: str,
    recent_results: list[dict[str, Any]],
    classroom_id: Optional[str],
    status: Optional[str] = None,
    limit: int = 10,
    selected_result_id: Optional[str] = None,
    current_user: Optional[dict] = None,
) -> str:
    latest = _summary(latest_payload)
    latest["source_kind"] = latest_source_kind
    latest["stored_path"] = str(latest_source_path)
    filter_value = html.escape(classroom_id or "")
    status_value = status or ""
    selected_result_value = html.escape(selected_result_id or "")
    user_identity = _identity_bar(current_user)

    recent_rows = "".join(_recent_row(item) for item in recent_results)
    if not recent_rows:
        recent_rows = '<tr><td colspan="9">No matching analysis results are available.</td></tr>'

    question_items = "".join(
        f"<li><strong>{html.escape(str(event.get('event_id', 'unknown')))}</strong>: "
        f"{html.escape(_stringify(event.get('text')))} "
        f"({html.escape(_stringify(event.get('start_sec')))}s - {html.escape(_stringify(event.get('end_sec')))}s, "
        f"{html.escape(_stringify(event.get('question_type')))})</li>"
        for event in latest.get("question_events", [])
    ) or "<li>No teacher question events are available yet.</li>"

    zone_items = "".join(
        f"<li><strong>{html.escape(zone_name.title())}</strong>: "
        f"attention {html.escape(_ratio(latest.get('zones', {}).get(zone_name, {}).get('avg_attention_ratio')))}, "
        f"activity {html.escape(_ratio(latest.get('zones', {}).get(zone_name, {}).get('active_ratio')))}</li>"
        for zone_name in ["front", "middle", "back"]
    )

    curve_items = "".join(
        [
            f"<li><strong>Attention curve</strong>: {html.escape(_curve(latest.get('attention_curve', [])))}</li>",
            f"<li><strong>Heat curve</strong>: {html.escape(_curve(latest.get('heat_curve', [])))}</li>",
            f"<li><strong>Activity curve</strong>: {html.escape(_curve(latest.get('activity_curve', [])))}</li>",
        ]
    )

    stage_items = "".join(
        f"<li><strong>{html.escape(key)}</strong>: {html.escape(_ratio(value))}</li>"
        for key, value in (latest.get("stage_distribution") or {}).items()
    ) or "<li>No stage distribution is available yet.</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cloud Classroom Results Center</title>
  <style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 0; background: radial-gradient(circle at top left, #e8f2ff, #f7f9fc 38%, #eef4fb); color: #1f2937; }}
    .page {{ max-width: 1240px; margin: 0 auto; padding: 24px; display: flex; flex-direction: column; gap: 18px; }}
    .hero, .grid {{ display: grid; gap: 16px; }}
    .hero {{ margin-bottom: 18px; }}
    .grid {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-bottom: 18px; }}
    .card {{ background: rgba(255, 255, 255, 0.94); border: 1px solid rgba(219, 231, 255, 0.82); border-radius: 18px; padding: 18px; box-shadow: 0 14px 36px rgba(15, 23, 42, 0.09); }}
    h1, h2 {{ margin-top: 0; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }}
    .metric {{ background: #f8fbff; border: 1px solid #dbe7ff; border-radius: 12px; padding: 12px; }}
    .metric-label {{ display: block; color: #64748b; font-size: 13px; margin-bottom: 6px; }}
    .metric-value {{ font-size: 24px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
    th {{ color: #64748b; font-size: 13px; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 8px; }}
    .muted {{ color: #6b7280; }}
    .filter-form {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: end; margin: 12px 0 16px; }}
    input, select {{ min-width: 180px; border: 1px solid #d1d5db; border-radius: 10px; padding: 10px 12px; font-size: 14px; background: #fff; }}
    button, .link-button {{ border: 0; border-radius: 10px; padding: 10px 14px; font-weight: 700; text-decoration: none; display: inline-block; }}
    button {{ background: #165dff; color: #fff; }}
    .link-button {{ background: #eef2f7; color: #1f2937; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #eef4ff; color: #165dff; font-size: 12px; font-weight: 700; }}
    .badge.sample {{ background: #fff7ed; color: #c2410c; }}
    .badge.reviewed {{ background: #ecfdf5; color: #047857; }}
    .badge.archived {{ background: #f3f4f6; color: #4b5563; }}
    .action-button {{ background: #eef2f7; color: #1f2937; margin: 2px; cursor: pointer; }}
    .danger-light {{ background: #fff7ed; color: #c2410c; }}
    .detail-box {{ background: #0f172a; color: #e5e7eb; border-radius: 12px; padding: 14px; white-space: pre-wrap; overflow-x: auto; }}
    .error {{ color: #b91c1c; font-weight: 700; }}
    .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-top: 16px; }}
    .chart-panel {{ border: 1px solid #e5e7eb; border-radius: 14px; padding: 12px; background: #fbfdff; }}
    .chart-title {{ margin: 0 0 8px; color: #334155; font-size: 15px; }}
    .chart-box {{ width: 100%; height: 300px; }}
    .brand-card {{ background: linear-gradient(135deg, #0f172a, #1d4ed8); color: #fff; }}
    .brand-card .muted {{ color: #dbeafe; }}
    .console-badge {{ display: inline-block; margin-bottom: 10px; padding: 5px 12px; border-radius: 999px; background: rgba(255,255,255,0.14); color: #bfdbfe; font-weight: 800; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }}
    .pipeline {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    .pipeline span {{ padding: 7px 12px; border-radius: 999px; background: rgba(255,255,255,0.14); font-weight: 700; }}
    .identity {{ display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; color: #475569; font-size: 13px; }}
    .logout {{ border: 0; border-radius: 10px; padding: 8px 10px; font-weight: 800; cursor: pointer; background: #0f172a; color: #fff; }}
    .analysis-card {{ order: 2; }}
    .results-card {{ order: 3; }}
    .debug-card {{ order: 4; }}
    .system-card {{ order: 5; }}
    .analysis-layout {{ display: grid; grid-template-columns: minmax(420px, 1.05fr) minmax(320px, 0.95fr); gap: 16px; align-items: stretch; }}
    .video-box {{ min-height: 300px; border-radius: 16px; background: linear-gradient(145deg, #07111f, #111827); color: #e5e7eb; display: grid; place-items: center; padding: 16px; text-align: center; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08); }}
    .video-box video {{ width: 100%; max-height: 420px; border-radius: 14px; background: #000; }}
    .event-list {{ list-style: none; padding-left: 0; max-height: 300px; overflow: auto; }}
    .event-list li {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 8px 10px; cursor: pointer; background: #fff; font-size: 13px; }}
    .event-list li.active {{ border-color: #165dff; background: #eef4ff; }}
    .feedback-box {{ background: #f8fbff; border: 1px solid #dbe7ff; border-radius: 14px; padding: 14px; line-height: 1.7; }}
    .section-kicker {{ color: #165dff; font-size: 12px; font-weight: 800; letter-spacing: .08em; margin: 0 0 6px; text-transform: uppercase; }}
    .score-strip {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 12px 0; }}
    .score-card {{ border-radius: 14px; padding: 12px; background: linear-gradient(180deg, #f8fbff, #eef4ff); border: 1px solid #dbe7ff; }}
    .score-card strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    details.debug-details summary {{ cursor: pointer; font-weight: 800; color: #334155; }}
    details.debug-details[open] {{ border-color: #cbd5e1; }}
    @media (max-width: 860px) {{ .analysis-layout {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="page">
    {user_identity}
    <section class="hero card brand-card" data-marker="teacher-analysis-center">
      <span class="console-badge">Teacher Console</span>
      <h1>Intelligent Classroom Behavior Analysis and Teaching Feedback Platform</h1>
      <p class="muted">Teacher Classroom Analysis Center for one captured classroom session: video evidence, behavior charts, key events, and teaching feedback.</p>
      <div class="pipeline" data-marker="data-pipeline-status">
        <span>Capture</span><span>-></span><span>Local Analysis</span><span>-></span><span>Cloud</span>
      </div>
      <div class="metrics">
        <div class="metric"><span class="metric-label">Classroom</span><div class="metric-value">{html.escape(_stringify(latest.get("classroom_id")))}</div></div>
        <div class="metric"><span class="metric-label">Source Host</span><div class="metric-value">{html.escape(_stringify(latest.get("source_host")))}</div></div>
        <div class="metric"><span class="metric-label">Generated At</span><div class="metric-value">{html.escape(_stringify(latest.get("generated_at")))}</div></div>
        <div class="metric"><span class="metric-label">Feedback Score</span><div class="metric-value">{html.escape(_score(latest.get("feedback_score")))}</div></div>
        <div class="metric"><span class="metric-label">Attention Score</span><div class="metric-value">{html.escape(_score(latest.get("attention_score")))}</div></div>
        <div class="metric"><span class="metric-label">Response Score</span><div class="metric-value">{html.escape(_score(latest.get("response_score")))}</div></div>
      </div>
      <div class="metrics">
        <div class="metric"><span class="metric-label">Teacher Question Count</span><div class="metric-value">{html.escape(_number(latest.get("teacher_question_count")))}</div></div>
        <div class="metric"><span class="metric-label">Avg Attention Ratio</span><div class="metric-value">{html.escape(_ratio(latest.get("avg_attention_ratio")))}</div></div>
        <div class="metric"><span class="metric-label">Response Success Rate</span><div class="metric-value">{html.escape(_ratio(latest.get("response_success_rate")))}</div></div>
        <div class="metric"><span class="metric-label">Estimated Student Count</span><div class="metric-value">{html.escape(_number(latest.get("estimated_student_count")))}</div></div>
        <div class="metric"><span class="metric-label">Hand Raise Events</span><div class="metric-value">{html.escape(_number(latest.get("hand_raise_event_count")))}</div></div>
        <div class="metric"><span class="metric-label">Window Size</span><div class="metric-value">{html.escape(_number(latest.get("window_size_seconds")))}s</div></div>
      </div>
      <p><strong>Summary:</strong> {html.escape(_stringify(latest.get("summary_text")))}</p>
    </section>

    <section class="card results-card">
      <h2>Recent Classroom Results</h2>
      <form class="filter-form" method="get" action="/dashboard">
        <div>
          <label for="classroom_id" class="muted">Filter by classroom_id</label>
          <select id="classroom_id" name="classroom_id" data-current="{filter_value}">
            <option value="">All classrooms</option>
            {_classroom_option(classroom_id)}
          </select>
        </div>
        <div>
          <label for="status" class="muted">Filter by status</label>
          <select id="status" name="status">
            <option value="" {_selected(status_value, "")}>All statuses</option>
            <option value="raw" {_selected(status_value, "raw")}>raw</option>
            <option value="reviewed" {_selected(status_value, "reviewed")}>reviewed</option>
            <option value="archived" {_selected(status_value, "archived")}>archived</option>
          </select>
        </div>
        <div>
          <label for="limit" class="muted">Limit</label>
          <select id="limit" name="limit">
            <option value="10" {_limit_option(limit, 10)}>10</option>
            <option value="20" {_limit_option(limit, 20)}>20</option>
            <option value="50" {_limit_option(limit, 50)}>50</option>
          </select>
        </div>
        <div><button type="submit">Apply Filter</button></div>
        <div><a class="link-button" href="/dashboard">Clear Filter</a></div>
        <div><button type="submit" class="action-button">Refresh</button></div>
      </form>
      <table>
        <thead>
          <tr><th>Analysis</th><th>Classroom</th><th>Lesson</th><th>Created</th><th>Feedback</th><th>Status</th><th>Source</th><th>Actions</th></tr>
        </thead>
        <tbody>{recent_rows}</tbody>
      </table>
    </section>

    <section id="chart-app" class="card analysis-card" data-marker="classroom-analysis-detail" data-initial-result-id="{selected_result_value}">
      <p class="section-kicker">Live Classroom Session</p>
      <h2>Selected Classroom Analysis</h2>
      <p class="muted">A single-session teacher view combining video evidence, behavior timeline, event distribution, and feedback summary.</p>
      <p v-if="error" class="error" v-text="error"></p>
      <div class="analysis-layout">
        <div>
          <h3>Classroom Video</h3>
          <div id="video-area" class="video-box" data-marker="video-area">
            <video v-if="video.status === 'playable'" id="classroom-video" controls :src="video.video_url"></video>
            <div v-else-if="video.status === 'pending'">
              <strong>Video pending sync</strong>
              <p>Captured evidence exists, but no playable cloud URL is available yet.</p>
              <p class="muted" v-text="video.raw_video_path || video.video_id"></p>
            </div>
            <div v-else>
              <strong>No playable video</strong>
              <p>This result can still be reviewed through charts, events, and raw analysis data.</p>
            </div>
          </div>
          <h3>Teaching Feedback Summary</h3>
          <div class="feedback-box" data-marker="teaching-feedback-summary">
            <p v-text="summary.summary_text || 'No feedback summary available yet.'"></p>
            <div class="score-strip">
              <div class="score-card"><span class="muted">Feedback</span><strong v-text="formatScore(summary.feedback_score)"></strong></div>
              <div class="score-card"><span class="muted">Attention</span><strong v-text="formatScore(summary.attention_score)"></strong></div>
              <div class="score-card"><span class="muted">Response</span><strong v-text="formatScore(summary.response_score)"></strong></div>
            </div>
            <p><strong>Status:</strong> <span v-text="selectedDetail && selectedDetail.status"></span></p>
            <button type="button" class="action-button" @click="updateSelectedStatus('reviewed')">Mark reviewed</button>
            <button type="button" class="action-button danger-light" @click="updateSelectedStatus('archived')">Archive</button>
          </div>
        </div>
        <div>
          <h3>Key Event List</h3>
          <ul class="event-list" data-marker="key-event-list">
            <li v-for="event in selectedEvents" :key="event.event_id" :class="{{active: activeEventId === event.event_id}}" @click="jumpToEvent(event)">
              <strong v-text="event.event_id"></strong>
              <span> - </span>
              <span v-text="event.event_type || event.question_type || 'unknown'"></span>
              <br />
              <span v-text="event.text || 'No event text'"></span>
              <br />
              <small v-text="'Start: ' + (event.start_sec || 0) + 's'"></small>
            </li>
          </ul>
        </div>
      </div>
      <div class="chart-grid">
        <div class="chart-panel">
          <h3 class="chart-title">Attention / Activity Timeline</h3>
          <div id="attention-activity-chart" class="chart-box" data-marker="attention-activity-chart"></div>
        </div>
        <div class="chart-panel">
          <h3 class="chart-title">Teaching Stage Distribution</h3>
          <div id="stage-distribution-chart" class="chart-box" data-marker="stage-distribution-chart"></div>
        </div>
        <div class="chart-panel">
          <h3 class="chart-title">Front / Middle / Back Zone Performance</h3>
          <div id="zone-performance-chart" class="chart-box" data-marker="zone-performance-chart"></div>
        </div>
        <div class="chart-panel">
          <h3 class="chart-title">Event Distribution</h3>
          <div id="event-distribution-chart" class="chart-box" data-marker="event-distribution-chart"></div>
        </div>
      </div>
    </section>

    <section class="card debug-card">
      <details class="debug-details" data-marker="debug-raw-data">
        <summary>Debug / Raw Data</summary>
        <p id="detail-status" class="muted">Raw detail follows the currently selected classroom result.</p>
        <div id="detail-panel" class="detail-box">Waiting for selected detail...</div>
        <div class="grid">
          <section>
            <h3>Teacher Question Events</h3>
            <ul>{question_items}</ul>
          </section>
          <section>
            <h3>Stage Distribution</h3>
            <ul>{stage_items}</ul>
          </section>
          <section>
            <h3>Zone Summary</h3>
            <ul>{zone_items}</ul>
          </section>
          <section>
            <h3>Timeline Curves</h3>
            <ul>{curve_items}</ul>
          </section>
        </div>
      </details>
    </section>

    <section class="card system-card">
      <h2>System Note</h2>
      <p class="muted">Current results are read from {html.escape(_stringify(latest_source_kind))} JSON and displayed under schema V1.1. Future video browsing and MP4 archive pages should connect to this center as supporting views rather than replacing it.</p>
    </section>
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <script>
    const chartInstances = {{}};

    function chartById(id) {{
      if (chartInstances[id]) {{
        chartInstances[id].dispose();
      }}
      chartInstances[id] = echarts.init(document.getElementById(id));
      return chartInstances[id];
    }}

    function countBy(items, key, fallback) {{
      return items.reduce((acc, item) => {{
        const value = item[key] || fallback;
        acc[value] = (acc[value] || 0) + 1;
        return acc;
      }}, {{}});
    }}

    function emptyGraphic(isEmpty, text = "No data available") {{
      return isEmpty ? {{
        type: "text",
        left: "center",
        top: "middle",
        style: {{ text, fill: "#94a3b8", fontSize: 14, fontWeight: 700 }}
      }} : null;
    }}

    const chartApp = Vue.createApp({{
      data() {{
        return {{
          items: [],
          classrooms: [],
          selectedDetail: null,
          activeEventId: "",
          initialResultId: "",
          error: ""
        }};
      }},
      async mounted() {{
        const chartRoot = document.getElementById("chart-app");
        this.initialResultId = (chartRoot && chartRoot.dataset.initialResultId) || "";
        await this.loadCharts();
        window.addEventListener("resize", () => {{
          Object.values(chartInstances).forEach((chart) => chart.resize());
        }});
      }},
      methods: {{
        async loadCharts() {{
          try {{
            if (!window.echarts) {{
              throw new Error("ECharts failed to load");
            }}
            const params = new URLSearchParams(window.location.search);
            params.set("limit", "50");
            const recentResponse = await fetch(`/api/teacher/results/recent?${{params.toString()}}`);
            if (!recentResponse.ok) {{
              throw new Error(`recent HTTP ${{recentResponse.status}}`);
            }}
            const recentPayload = await recentResponse.json();
            this.items = recentPayload.items || [];

            const classroomResponse = await fetch("/api/teacher/classrooms");
            if (!classroomResponse.ok) {{
              throw new Error(`classrooms HTTP ${{classroomResponse.status}}`);
            }}
            const classroomPayload = await classroomResponse.json();
            this.classrooms = classroomPayload.items || [];
            this.renderClassroomFilter();

            const firstId = this.initialResultId || (this.items[0] && (this.items[0].result_id || this.items[0].analysis_id));
            if (firstId) {{
              const detailResponse = await fetch(`/api/teacher/results/${{encodeURIComponent(firstId)}}`);
              if (detailResponse.ok) {{
                const detailPayload = await detailResponse.json();
                this.setSelectedDetail(detailPayload.result || null);
              }} else {{
                this.error = `Requested result ${{firstId}} could not be loaded. Select another result from the list.`;
              }}
            }}
            if (!this.error) {{
              this.error = "";
            }}
            this.$nextTick(() => this.renderCharts());
          }} catch (error) {{
            this.error = `Loading charts failed: ${{error}}`;
          }}
        }},
        renderCharts() {{
          this.renderAttentionActivityTimeline();
          this.renderStageDistribution();
          this.renderZonePerformance();
          this.renderEventDistribution();
        }},
        setSelectedDetail(result) {{
          this.selectedDetail = result || null;
          this.activeEventId = "";
          this.updateRawDetailPanel(result || null);
          this.$nextTick(() => this.renderCharts());
        }},
        updateRawDetailPanel(result) {{
          const statusEl = document.getElementById("detail-status");
          const panelEl = document.getElementById("detail-panel");
          if (!statusEl || !panelEl) {{
            return;
          }}
          if (!result) {{
            statusEl.textContent = "Waiting for selected classroom detail.";
            panelEl.textContent = "No selected detail payload has been loaded yet.";
            return;
          }}
          statusEl.textContent = `Loaded ${{result.result_id || result.analysis_id || "selected result"}}`;
          statusEl.className = "muted";
          panelEl.textContent = JSON.stringify(this.detailSnapshot(result), null, 2);
        }},
        detailSnapshot(result) {{
          return {{
            result_id: result.result_id,
            classroom_id: result.classroom_id,
            classroom_name: result.classroom_name,
            lesson_title: result.lesson_title,
            status: result.status,
            score: result.score,
            video: result.video,
            raw_path: result.raw_path,
            summary: result.summary,
            timeline: result.timeline,
            stage_distribution: result.stage_distribution,
            zones: result.zones,
            events: result.events,
            raw_payload: result.raw_payload
          }};
        }},
        formatScore(value) {{
          const number = Number(value || 0);
          return Number.isFinite(number) ? number.toFixed(1) : "0.0";
        }},
        renderClassroomFilter() {{
          const select = document.getElementById("classroom_id");
          if (!select) {{
            return;
          }}
          const current = select.dataset.current || "";
          select.innerHTML = "";
          const allOption = document.createElement("option");
          allOption.value = "";
          allOption.textContent = "All classrooms";
          select.appendChild(allOption);
          this.classrooms.forEach((item) => {{
            const id = item.classroom_id || "unknown";
            const label = item.classroom_name || id;
            const option = document.createElement("option");
            option.value = id;
            option.textContent = label;
            option.selected = id === current;
            select.appendChild(option);
          }});
          if (current && !this.classrooms.some((item) => item.classroom_id === current)) {{
            const option = document.createElement("option");
            option.value = current;
            option.textContent = current;
            option.selected = true;
            select.appendChild(option);
          }}
        }},
        renderAttentionActivityTimeline() {{
          const timeline = (this.selectedDetail && this.selectedDetail.timeline) || {{}};
          const windowSize = timeline.window_size_seconds || 30;
          const attention = timeline.attention_curve || [];
          const activity = timeline.activity_curve || [];
          const maxLength = Math.max(attention.length, activity.length);
          const xAxis = Array.from({{length: maxLength}}, (_, index) => `${{Math.round(index * windowSize)}}s`);
          const isEmpty = maxLength === 0;
          chartById("attention-activity-chart").setOption({{
            tooltip: {{ trigger: "axis" }},
            legend: {{ data: ["attention", "activity"] }},
            grid: {{ left: 42, right: 24, bottom: 46, top: 46 }},
            graphic: emptyGraphic(isEmpty),
            xAxis: {{
              type: "category",
              data: xAxis
            }},
            yAxis: {{ type: "value", min: 0, max: 1, axisLabel: {{ formatter: "{{value}}" }} }},
            series: [
              {{ name: "attention", type: "line", smooth: true, symbol: "none", lineStyle: {{ width: 3 }}, areaStyle: {{ opacity: 0.08 }}, data: attention }},
              {{ name: "activity", type: "line", smooth: true, symbol: "none", lineStyle: {{ width: 3 }}, areaStyle: {{ opacity: 0.08 }}, data: activity }}
            ]
          }});
        }},
        renderStageDistribution() {{
          const stage = (this.selectedDetail && this.selectedDetail.stage_distribution) || {{}};
          const labels = [
            ["exposition", "exposition_ratio"],
            ["question", "question_ratio"],
            ["discussion", "discussion_ratio"],
            ["summary", "summary_ratio"],
            ["management", "management_ratio"]
          ];
          const stageData = labels
            .map(([name, key]) => ({{ name, value: Number(stage[key] || 0) }}))
            .filter((item) => item.value > 0.0001);
          const isEmpty = stageData.length === 0;
          chartById("stage-distribution-chart").setOption({{
            tooltip: {{ trigger: "item" }},
            legend: {{ bottom: 0, type: "scroll" }},
            graphic: emptyGraphic(isEmpty),
            series: [{{
              type: "pie",
              radius: ["42%", "70%"],
              minAngle: 8,
              avoidLabelOverlap: true,
              label: {{
                formatter: "{{b}}\\n{{d}}%",
                overflow: "truncate",
                width: 90
              }},
              labelLine: {{ length: 10, length2: 6 }},
              data: isEmpty ? [] : stageData
            }}]
          }});
        }},
        renderZonePerformance() {{
          const zones = (this.selectedDetail && this.selectedDetail.zones) || {{}};
          const zoneNames = ["front", "middle", "back"];
          const attentionValues = zoneNames.map((name) => Number((zones[name] || {{}}).avg_attention_ratio || 0));
          const activityValues = zoneNames.map((name) => Number((zones[name] || {{}}).active_ratio || 0));
          const isEmpty = attentionValues.concat(activityValues).every((value) => value === 0);
          chartById("zone-performance-chart").setOption({{
            tooltip: {{ trigger: "axis" }},
            legend: {{ data: ["attention", "activity"] }},
            grid: {{ left: 42, right: 20, bottom: 42, top: 24 }},
            graphic: emptyGraphic(isEmpty, "Zone data unavailable"),
            xAxis: {{
              type: "category",
              data: zoneNames
            }},
            yAxis: {{ type: "value", min: 0, max: 1 }},
            series: [
              {{ name: "attention", type: "bar", barMaxWidth: 34, data: attentionValues, label: {{ show: true, position: "top", formatter: "{{c}}" }} }},
              {{ name: "activity", type: "bar", barMaxWidth: 34, data: activityValues, label: {{ show: true, position: "top", formatter: "{{c}}" }} }}
            ]
          }});
        }},
        renderEventDistribution() {{
          const events = this.selectedEvents;
          const counts = events.reduce((acc, event) => {{
            const type = event.event_type || event.question_type || "unknown";
            acc[type] = (acc[type] || 0) + 1;
            return acc;
          }}, {{}});
          const names = Object.keys(counts);
          chartById("event-distribution-chart").setOption({{
            tooltip: {{ trigger: "axis" }},
            grid: {{ left: 42, right: 20, bottom: 68, top: 24 }},
            graphic: emptyGraphic(names.length === 0, "No events detected"),
            xAxis: {{ type: "category", data: names, axisLabel: {{ rotate: 25, width: 100, overflow: "truncate" }} }},
            yAxis: {{ type: "value", minInterval: 1 }},
            series: [{{
              name: "events",
              type: "bar",
              barMaxWidth: 42,
              label: {{ show: true, position: "top" }},
              data: names.map((name) => counts[name])
            }}]
          }});
        }},
        jumpToEvent(event) {{
          this.activeEventId = event.event_id || "";
          const video = document.getElementById("classroom-video");
          if (video && this.video.status === "playable" && event.start_sec !== undefined) {{
            video.currentTime = Number(event.start_sec || 0);
            video.play().catch(() => {{}});
          }}
        }},
        async updateSelectedStatus(status) {{
          if (!this.selectedDetail || !this.selectedDetail.result_id) {{
            return;
          }}
          await updateResultStatus(this.selectedDetail.result_id, status, false);
          const response = await fetch(`/api/teacher/results/${{encodeURIComponent(this.selectedDetail.result_id)}}`);
          if (response.ok) {{
            const payload = await response.json();
            this.setSelectedDetail(payload.result || null);
          }}
        }}
      }},
      computed: {{
        video() {{
          return (this.selectedDetail && this.selectedDetail.video) || {{status: "missing"}};
        }},
        summary() {{
          return (this.selectedDetail && this.selectedDetail.summary) || {{}};
        }},
        selectedEvents() {{
          return (this.selectedDetail && this.selectedDetail.events) || [];
        }}
      }}
    }}).mount("#chart-app");

    async function loadResultDetail(resultId) {{
      const statusEl = document.getElementById("detail-status");
      const panelEl = document.getElementById("detail-panel");
      statusEl.textContent = "Loading result detail...";
      try {{
        const response = await fetch(`/api/teacher/results/${{encodeURIComponent(resultId)}}`);
        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}
        const payload = await response.json();
        const result = payload.result || {{}};
        panelEl.textContent = JSON.stringify({{
          result_id: result.result_id,
          classroom_id: result.classroom_id,
          classroom_name: result.classroom_name,
          lesson_title: result.lesson_title,
          status: result.status,
          score: result.score,
          video: result.video,
          raw_path: result.raw_path,
          summary: result.summary,
          timeline: result.timeline,
          stage_distribution: result.stage_distribution,
          zones: result.zones,
          events: result.events,
          raw_payload: result.raw_payload
        }}, null, 2);
        if (chartApp && typeof chartApp.setSelectedDetail === "function") {{
          chartApp.setSelectedDetail(result);
        }}
        statusEl.textContent = `Loaded ${{resultId}}`;
        statusEl.className = "muted";
      }} catch (error) {{
        statusEl.textContent = "Loading result detail failed. Check backend service.";
        statusEl.className = "error";
        panelEl.textContent = String(error);
      }}
    }}

    async function updateResultStatus(resultId, status, reloadPage = true) {{
      const statusEl = document.getElementById("detail-status");
      try {{
        const response = await fetch(`/api/teacher/results/${{encodeURIComponent(resultId)}}/status`, {{
          method: "PATCH",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{status}})
        }});
        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}
        const payload = await response.json();
        const statusBadge = Array.from(document.querySelectorAll("[data-result-status]"))
          .find((element) => element.getAttribute("data-result-status") === resultId);
        if (statusBadge) {{
          statusBadge.textContent = status;
          statusBadge.className = `badge ${{status === "reviewed" || status === "archived" ? status : ""}}`;
        }}
        if (chartApp && Array.isArray(chartApp.items)) {{
          chartApp.items = chartApp.items.map((item) => {{
            if ((item.result_id || item.analysis_id) === resultId) {{
              return Object.assign({{}}, item, (payload && payload.result) || {{}}, {{status}});
            }}
            return item;
          }});
        }}
        statusEl.textContent = `Updated ${{resultId}} to ${{status}}.`;
        if (reloadPage) {{
          statusEl.textContent = `Updated ${{resultId}} to ${{status}}. Refreshing list...`;
          window.location.reload();
        }}
      }} catch (error) {{
        statusEl.textContent = "Status update failed. Check backend service.";
        statusEl.className = "error";
      }}
    }}
  </script>
</body>
</html>"""


def _recent_row(item: dict[str, Any]) -> str:
    summary = item.get("summary") or {}
    analysis_id = _stringify(summary.get("analysis_id"))
    source_kind = _stringify(item.get("source_kind"))
    badge_class = "badge sample" if source_kind == "sample" else "badge"
    status = _stringify(summary.get("status") or item.get("status") or "raw")
    status_class = "badge " + html.escape(status if status in {"reviewed", "archived"} else "")
    lesson_title = _stringify(summary.get("lesson_title") or summary.get("video_id"))
    created_at = _stringify(summary.get("created_at") or summary.get("generated_at"))
    return (
        f"<tr data-result-id=\"{html.escape(analysis_id)}\">"
        f"<td>{html.escape(analysis_id)}</td>"
        f"<td>{html.escape(_stringify(summary.get('classroom_id')))}</td>"
        f"<td>{html.escape(lesson_title)}</td>"
        f"<td>{html.escape(created_at)}</td>"
        f"<td>{html.escape(_score(summary.get('feedback_score')))}</td>"
        f"<td><span class=\"{status_class.strip()}\" data-result-status=\"{html.escape(analysis_id)}\">{html.escape(status)}</span></td>"
        f"<td><span class=\"{badge_class}\">{html.escape(source_kind)}</span></td>"
        "<td>"
        f"<button class=\"action-button\" type=\"button\" onclick=\"loadResultDetail('{html.escape(analysis_id)}')\">Detail</button>"
        f"<button class=\"action-button\" type=\"button\" onclick=\"updateResultStatus('{html.escape(analysis_id)}','reviewed')\">reviewed</button>"
        f"<button class=\"action-button danger-light\" type=\"button\" onclick=\"updateResultStatus('{html.escape(analysis_id)}','archived')\">archived</button>"
        "</td>"
        "</tr>"
    )


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source") or {}
    time_info = payload.get("time") or {}
    summary = payload.get("summary") or {}
    teacher = payload.get("teacher") or {}
    students = payload.get("students") or {}
    timeline = payload.get("timeline") or {}
    return {
        "analysis_id": payload.get("analysis_id"),
        "classroom_id": payload.get("classroom_id"),
        "video_id": payload.get("video_id"),
        "source_kind": source.get("source_kind"),
        "source_path": source.get("source_path"),
        "source_host": source.get("source_host"),
        "recorded_at": time_info.get("recorded_at"),
        "generated_at": time_info.get("generated_at"),
        "duration_seconds": time_info.get("duration_seconds"),
        "feedback_score": summary.get("feedback_score"),
        "attention_score": summary.get("attention_score"),
        "response_score": summary.get("response_score"),
        "teacher_question_count": summary.get("teacher_question_count"),
        "avg_attention_ratio": summary.get("avg_attention_ratio"),
        "response_success_rate": summary.get("response_success_rate"),
        "summary_text": summary.get("summary_text"),
        "question_events": teacher.get("question_events") or [],
        "stage_distribution": teacher.get("stage_distribution") or {},
        "estimated_student_count": students.get("estimated_student_count"),
        "hand_raise_event_count": students.get("hand_raise_event_count"),
        "zones": students.get("zones") or {},
        "window_size_seconds": timeline.get("window_size_seconds"),
        "attention_curve": timeline.get("attention_curve") or [],
        "heat_curve": timeline.get("heat_curve") or [],
        "activity_curve": timeline.get("activity_curve") or [],
    }


def _ratio(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return _stringify(value)


def _score(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(round(float(value), 2))
    return _stringify(value)


def _number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(round(float(value), 2))
    return _stringify(value)


def _curve(values: list[Any]) -> str:
    if not values:
        return "N/A"
    return ", ".join(_ratio(value) for value in values)


def _selected(current: str, expected: str) -> str:
    return "selected" if current == expected else ""


def _limit_option(current: int, expected: int) -> str:
    return "selected" if int(current or 0) == expected else ""


def _classroom_option(classroom_id: Optional[str]) -> str:
    if not classroom_id:
        return ""
    escaped = html.escape(classroom_id)
    return f'<option value="{escaped}" selected>{escaped}</option>'


def _identity_bar(current_user: Optional[dict]) -> str:
    if not current_user:
        return ""
    display_name = html.escape(str(current_user.get("display_name") or current_user.get("username") or "User"))
    role = html.escape(str(current_user.get("role") or ""))
    return f"""
    <div class="identity" data-marker="phase29-user-identity">
      <span>{display_name} · {role}</span>
      <button class="logout" type="button" onclick="fetch('/api/auth/logout', {{method: 'POST'}}).finally(() => window.location.href='/login')">Logout</button>
    </div>
    """


def _stringify(value: Any) -> str:
    if value in (None, ""):
        return "N/A"
    return str(value)
