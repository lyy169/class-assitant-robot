"""Dashboard helpers aligned to classroom feedback JSON schema V1.1."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from .repository_interface import ResultRepository
from .ui_style import PHASE31_STYLE, role_label


def latest_result_or_404(
    repository: ResultRepository,
    classroom_id: Optional[str] = None,
) -> tuple[dict[str, Any], Path, str]:
    latest_result = repository.latest_result(classroom_id=classroom_id)
    if latest_result is None:
        raise HTTPException(status_code=404, detail="暂无可用课堂分析结果")
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
        recent_rows = '<tr><td colspan="9">当前筛选条件下暂无课堂分析结果。</td></tr>'

    question_items = "".join(
        f"<li><strong>{html.escape(str(event.get('event_id', '未知事件')))}</strong>: "
        f"{html.escape(_stringify(event.get('text')))} "
        f"({html.escape(_stringify(event.get('start_sec')))}s - {html.escape(_stringify(event.get('end_sec')))}s, "
        f"{html.escape(_stringify(event.get('question_type')))})</li>"
        for event in latest.get("question_events", [])
    ) or "<li>暂无教师提问事件。</li>"

    zone_items = "".join(
        f"<li><strong>{html.escape({'front': '前区', 'middle': '中区', 'back': '后区'}.get(zone_name, zone_name))}</strong>: "
        f"专注 {html.escape(_ratio(latest.get('zones', {}).get(zone_name, {}).get('avg_attention_ratio')))}, "
        f"活跃 {html.escape(_ratio(latest.get('zones', {}).get(zone_name, {}).get('active_ratio')))}</li>"
        for zone_name in ["front", "middle", "back"]
    )

    curve_items = "".join(
        [
            f"<li><strong>专注度曲线</strong>: {html.escape(_curve(latest.get('attention_curve', [])))}</li>",
            f"<li><strong>热度曲线</strong>: {html.escape(_curve(latest.get('heat_curve', [])))}</li>",
            f"<li><strong>活跃度曲线</strong>: {html.escape(_curve(latest.get('activity_curve', [])))}</li>",
        ]
    )

    stage_items = "".join(
        f"<li><strong>{html.escape(key)}</strong>: {html.escape(_ratio(value))}</li>"
        for key, value in (latest.get("stage_distribution") or {}).items()
    ) or "<li>暂无教学阶段分布。</li>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>课堂分析</title>
  {PHASE31_STYLE}
  <style>
    .brand-card {{ background: linear-gradient(135deg, #eff6ff, #ffffff 52%, #ecfeff); }}
    .console-badge {{ display:inline-block; margin-bottom:10px; padding:5px 12px; border-radius:999px; background:#e8f1ff; color:#1d4ed8; font-weight:900; font-size:12px; letter-spacing:.08em; }}
    .analysis-layout {{ display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: stretch; min-width: 0; }}
    .video-box {{ min-height: 420px; border-radius: 10px; background: linear-gradient(145deg, #07111f, #17315d); color: #e5e7eb; display: grid; place-items: center; padding: 18px; text-align: center; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08); }}
    .video-box video {{ width: 100%; max-height: 430px; border-radius: 10px; background: #000; }}
    .event-list {{ list-style: none; padding-left: 0; max-height: 360px; overflow: auto; }}
    .event-list li {{ border: 1px solid #e5edf6; border-radius: 14px; padding: 10px 12px; cursor: pointer; background: #fff; font-size: 13px; margin-bottom: 8px; }}
    .event-list li.active {{ border-color: #2563eb; background: #e8f1ff; }}
    .feedback-box {{ background: #f8fbff; border: 1px solid #dbe7ff; border-radius: 18px; padding: 16px; line-height: 1.7; }}
    .section-kicker {{ color: #2563eb; font-size: 12px; font-weight: 900; letter-spacing: .08em; margin: 0 0 6px; }}
    .score-strip {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 12px 0; }}
    .score-card {{ border-radius: 14px; padding: 12px; background: linear-gradient(180deg, #f8fbff, #eef4ff); border: 1px solid #dbe7ff; }}
    .score-card strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    .detail-box {{ background: #0f172a; color: #e5e7eb; border-radius: 12px; padding: 14px; white-space: pre-wrap; overflow: auto; max-height: 420px; }}
    .filter-form {{ display:flex; gap:10px; flex-wrap:wrap; align-items:end; margin:12px 0 16px; }}
    @media (max-width: 860px) {{ .analysis-layout {{ grid-template-columns: 1fr; }} .score-strip {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class="page">
    {_teacher_dashboard_nav(current_user)}
    <main class="page-main">
    {user_identity}
    <section class="hero card brand-card" data-marker="teacher-analysis-center">
      <span class="console-badge">课堂分析</span>
      <h1>单堂课堂证据与教学反馈仪表盘</h1>
      <p class="muted">把课堂视频证据、行为趋势、关键事件和教学建议整合到同一页，帮助教师完成有依据的复盘。</p>
      <div class="pipeline" data-marker="data-pipeline-status">
        <span>树莓派采集</span><span>-></span><span>本地分析</span><span>-></span><span>云端反馈</span>
      </div>
      <div class="metrics">
        <div class="metric"><span class="metric-label">班级</span><div class="metric-value">{html.escape(_stringify(latest.get("classroom_id")))}</div></div>
        <div class="metric"><span class="metric-label">来源主机</span><div class="metric-value">{html.escape(_stringify(latest.get("source_host")))}</div></div>
        <div class="metric"><span class="metric-label">生成时间</span><div class="metric-value">{html.escape(_stringify(latest.get("generated_at")))}</div></div>
        <div class="metric"><span class="metric-label">反馈分</span><div class="metric-value">{html.escape(_score(latest.get("feedback_score")))}</div></div>
        <div class="metric"><span class="metric-label">专注度</span><div class="metric-value">{html.escape(_score(latest.get("attention_score")))}</div></div>
        <div class="metric"><span class="metric-label">响应度</span><div class="metric-value">{html.escape(_score(latest.get("response_score")))}</div></div>
      </div>
      <div class="metrics">
        <div class="metric"><span class="metric-label">教师提问</span><div class="metric-value">{html.escape(_number(latest.get("teacher_question_count")))}</div></div>
        <div class="metric"><span class="metric-label">平均专注率</span><div class="metric-value">{html.escape(_ratio(latest.get("avg_attention_ratio")))}</div></div>
        <div class="metric"><span class="metric-label">响应成功率</span><div class="metric-value">{html.escape(_ratio(latest.get("response_success_rate")))}</div></div>
        <div class="metric"><span class="metric-label">学生人数估计</span><div class="metric-value">{html.escape(_number(latest.get("estimated_student_count")))}</div></div>
        <div class="metric"><span class="metric-label">举手事件</span><div class="metric-value">{html.escape(_number(latest.get("hand_raise_event_count")))}</div></div>
        <div class="metric"><span class="metric-label">分析窗口</span><div class="metric-value">{html.escape(_number(latest.get("window_size_seconds")))}s</div></div>
      </div>
      <p><strong>课堂结论：</strong> {html.escape(_stringify(latest.get("summary_text")))}</p>
    </section>

    <section id="chart-app" class="card analysis-card" data-marker="classroom-analysis-detail" data-initial-result-id="{selected_result_value}">
      <div class="section-title">
        <div>
          <p class="section-kicker">课堂证据与教学洞察</p>
          <h2>选中课堂分析</h2>
          <p class="muted">第一屏聚焦真实课堂证据、关键结论和可执行复盘动作，结果列表放在下方辅助切换。</p>
        </div>
        <div class="context-actions">
          <a class="button secondary" href="/teacher/reports">报告中心</a>
          <a class="button secondary" href="/teacher/trends">趋势洞察</a>
        </div>
      </div>
      <p v-if="error" class="error" v-text="error"></p>
      <div class="analysis-layout">
        <div class="evidence-panel">
          <div class="section-title">
            <div>
              <h3>课堂视频证据</h3>
              <p class="muted">有视频地址时直接播放；无视频时展示接入状态，不伪造课堂证据。</p>
            </div>
            <span class="visual-badge" v-text="video.status === 'playable' ? '视频可播放' : (video.status === 'pending' ? '待接入' : '暂无视频')"></span>
          </div>
          <div id="video-area" class="video-box" data-marker="video-area">
            <video v-if="video.status === 'playable'" id="classroom-video" controls :src="video.video_url"></video>
            <div v-else-if="video.status === 'pending'">
              <strong>课堂视频证据待接入</strong>
              <p>系统已检测到视频或采集信息，但当前没有可直接播放的云端视频地址。</p>
              <p class="muted" v-text="video.raw_video_path || video.video_id"></p>
            </div>
            <div v-else>
              <strong>暂无可播放视频</strong>
              <p>可先通过图表、事件和教学建议完成课堂复盘；视频格式处理不属于本阶段。</p>
            </div>
          </div>
          <div class="evidence-meta">
            <span class="badge" v-text="'班级 ' + (selectedDetail && selectedDetail.classroom_id || '未知')"></span>
            <span class="badge" v-text="'课堂 ' + (selectedDetail && selectedDetail.lesson_title || '未命名')"></span>
            <span class="badge" v-text="'时间 ' + (selectedDetail && (selectedDetail.created_at || selectedDetail.generated_at) || '未知')"></span>
          </div>
        </div>
        <aside class="insight-panel insight-stack">
          <p class="section-kicker">教学洞察</p>
          <h3>课堂结论与复盘动作</h3>
          <div class="large-score" v-text="formatScore(summary.feedback_score)"></div>
          <p class="muted">综合反馈分</p>
          <div class="feedback-box" data-marker="teaching-feedback-summary">
            <p v-text="summary.summary_text || '暂无教学反馈摘要。'"></p>
          </div>
          <div class="score-strip">
            <div class="score-card"><span class="muted">专注</span><strong v-text="formatScore(summary.attention_score)"></strong></div>
            <div class="score-card"><span class="muted">响应</span><strong v-text="formatScore(summary.response_score)"></strong></div>
            <div class="score-card"><span class="muted">事件</span><strong v-text="selectedEvents.length"></strong></div>
          </div>
          <div class="insight-item">
            <strong>复盘状态</strong>
            <p class="muted" v-text="statusText(selectedDetail && selectedDetail.status)"></p>
            <div class="action-row">
              <button type="button" class="action-button" @click="updateSelectedStatus('reviewed')">标记已复盘</button>
              <button type="button" class="action-button danger-light" @click="updateSelectedStatus('archived')">归档</button>
            </div>
          </div>
          <div>
            <h3>关键事件</h3>
          <ul class="event-list" data-marker="key-event-list">
            <li v-for="event in selectedEvents" :key="event.event_id" :class="{{active: activeEventId === event.event_id}}" @click="jumpToEvent(event)">
              <strong v-text="event.event_id"></strong>
              <span> - </span>
              <span v-text="event.event_type || event.question_type || '未知事件'"></span>
              <br />
              <span v-text="event.text || '暂无事件描述'"></span>
              <br />
              <small v-text="'开始：' + (event.start_sec || 0) + 's'"></small>
            </li>
          </ul>
          </div>
        </aside>
      </div>
      <section v-if="hasEnhanced" class="card insight-card" data-marker="phase32-enhanced-summary">
        <div class="section-title">
          <div>
            <p class="section-kicker">Phase 3.2 增强解释</p>
            <h2>分析可信度 / 评分解释</h2>
            <p class="muted">本区仅在本地端上传 enhanced JSON 字段时展示；旧数据缺字段时页面保持原有展示。</p>
          </div>
          <span class="badge">analysis_version {{ enhanced.analysis_version || '未标注' }}</span>
        </div>
        <div class="grid">
          <div class="record">
            <strong>分析可信度</strong>
            <p class="large-score" style="font-size:34px" v-text="formatConfidence(enhanced.quality_metrics && enhanced.quality_metrics.data_confidence)"></p>
            <p class="muted">algorithm_profile：<span v-text="formatInline(enhanced.algorithm_profile)"></span></p>
          </div>
          <div class="record">
            <strong>曲线口径</strong>
            <p>窗口：<span v-text="formatInline(enhanced.curve_metadata && enhanced.curve_metadata.window_seconds)"></span> 秒</p>
            <p>平滑：<span v-text="formatInline(enhanced.curve_metadata && enhanced.curve_metadata.smoothing)"></span></p>
          </div>
          <div class="record">
            <strong>证据摘要</strong>
            <p v-for="entry in evidenceSummaryEntries" :key="entry.key">
              <span class="muted" v-text="entry.label"></span>：<span v-text="entry.value"></span>
            </p>
          </div>
        </div>
        <div class="grid" v-if="scoreBreakdownEntries.length">
          <div class="mini-stat" v-for="entry in scoreBreakdownEntries" :key="entry.key">
            <span v-text="entry.label"></span>
            <strong v-text="entry.value"></strong>
          </div>
        </div>
        <div class="list" v-if="enhancedIssuesTop.length">
          <h3>增强问题 Top 3</h3>
          <div class="record" v-for="issue in enhancedIssuesTop" :key="issueKey(issue)">
            <div class="record-head">
              <strong v-text="issueLabel(issue)"></strong>
              <span class="badge" v-text="issue.severity || 'unknown'"></span>
            </div>
            <p><strong>原因：</strong><span v-text="issue.reason || '暂无原因说明'"></span></p>
            <p><strong>证据：</strong><span v-text="issue.evidence || '暂无证据说明'"></span></p>
            <p><strong>建议：</strong><span v-text="issue.suggestion || '暂无建议'"></span></p>
          </div>
        </div>
      </section>
      <div class="dashboard-grid">
        <div class="chart-panel dashboard-main">
          <h3 class="chart-title">专注度 / 活跃度时间线</h3>
          <p class="muted">主图用于定位课堂参与低谷、互动提问点和复盘重点。</p>
          <div id="attention-activity-chart" class="chart-box chart-hero" data-marker="attention-activity-chart"></div>
        </div>
        <div class="insight-panel dashboard-side">
          <h3 class="chart-title">课堂参与节奏条</h3>
          <p class="muted">绿色表示参与较好，琥珀表示需要观察，红色表示建议重点复盘；圆点代表提问或互动节点。</p>
          <div class="heat-strip">
            <span class="strip-cell high"></span><span class="strip-cell medium question"></span><span class="strip-cell high"></span><span class="strip-cell medium"></span>
            <span class="strip-cell low"></span><span class="strip-cell low question"></span><span class="strip-cell medium"></span><span class="strip-cell high"></span>
            <span class="strip-cell high question"></span><span class="strip-cell medium"></span><span class="strip-cell high"></span><span class="strip-cell medium"></span>
          </div>
          <h3>复盘提示</h3>
          <p class="muted">结合视频证据和关键事件，优先复盘曲线低谷附近的教学节奏、等待时间和互动引导。</p>
        </div>
      </div>
      <div class="grid">
        <div class="chart-panel">
          <h3 class="chart-title">教学阶段分布</h3>
          <div id="stage-distribution-chart" class="chart-box" data-marker="stage-distribution-chart"></div>
        </div>
        <div class="chart-panel">
          <h3 class="chart-title">前 / 中 / 后区域表现</h3>
          <div id="zone-performance-chart" class="chart-box" data-marker="zone-performance-chart"></div>
        </div>
        <div class="chart-panel">
          <h3 class="chart-title">事件分布</h3>
          <div id="event-distribution-chart" class="chart-box" data-marker="event-distribution-chart"></div>
        </div>
      </div>
    </section>

    <section class="card results-card">
      <details id="dashboard-results-details">
        <summary><strong>课堂结果列表与筛选</strong> <span class="muted">用于切换其他课堂，默认折叠以突出单堂课堂分析。</span></summary>
        <form class="filter-form" method="get" action="/dashboard">
          <div>
            <label for="classroom_id" class="muted">班级筛选</label>
            <select id="classroom_id" name="classroom_id" data-current="{filter_value}">
              <option value="">全部班级</option>
              {_classroom_option(classroom_id)}
            </select>
          </div>
          <div>
            <label for="status" class="muted">状态筛选</label>
            <select id="status" name="status">
              <option value="" {_selected(status_value, "")}>全部状态</option>
              <option value="raw" {_selected(status_value, "raw")}>待复盘</option>
              <option value="reviewed" {_selected(status_value, "reviewed")}>已复盘</option>
              <option value="archived" {_selected(status_value, "archived")}>已归档</option>
            </select>
          </div>
          <div>
            <label for="limit" class="muted">数量</label>
            <select id="limit" name="limit">
              <option value="10" {_limit_option(limit, 10)}>10</option>
              <option value="20" {_limit_option(limit, 20)}>20</option>
              <option value="50" {_limit_option(limit, 50)}>50</option>
            </select>
          </div>
          <div><button type="submit">筛选</button></div>
          <div><a class="link-button" href="/dashboard">清除筛选</a></div>
          <div><button type="submit" class="action-button">刷新</button></div>
        </form>
        <div id="dashboard-results-mount" class="dashboard-results-mount empty">展开后加载课堂结果列表。</div>
        <template id="dashboard-results-template">
          <div class="table-scroll">
            <table>
              <thead>
                <tr><th>分析ID</th><th>班级</th><th>课堂</th><th>创建时间</th><th>反馈</th><th>状态</th><th>来源</th><th>操作</th></tr>
              </thead>
              <tbody>{recent_rows}</tbody>
            </table>
          </div>
        </template>
      </details>
    </section>

    <section class="card debug-card">
      <details class="debug-details" data-marker="debug-raw-data">
        <summary>调试 / 原始数据</summary>
        <p id="detail-status" class="muted">原始详情会跟随当前选中的课堂结果更新。</p>
        <div id="detail-panel" class="detail-box">等待选择课堂详情...</div>
        <div class="grid">
          <section>
            <h3>教师提问事件</h3>
            <ul>{question_items}</ul>
          </section>
          <section>
            <h3>阶段结构</h3>
            <ul>{stage_items}</ul>
          </section>
          <section>
            <h3>区域表现摘要</h3>
            <ul>{zone_items}</ul>
          </section>
          <section>
            <h3>时间线曲线</h3>
            <ul>{curve_items}</ul>
          </section>
        </div>
      </details>
    </section>

    <section class="card system-card">
      <h2>系统说明</h2>
      <p class="muted">当前结果读取自 {html.escape(_stringify(latest_source_kind))} JSON，并按 schema V1.1 展示。后续视频浏览和 MP4 归档页面应作为辅助视图接入本分析中心，而不是替代它。</p>
    </section>
    </main>
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <script>
    document.addEventListener("DOMContentLoaded", () => {{
      const details = document.getElementById("dashboard-results-details");
      const mount = document.getElementById("dashboard-results-mount");
      const template = document.getElementById("dashboard-results-template");
      const loadResultsTable = () => {{
        if (!mount || !template || mount.dataset.loaded === "true") {{
          return;
        }}
        mount.className = "dashboard-results-mount";
        mount.innerHTML = template.innerHTML;
        mount.dataset.loaded = "true";
      }};
      if (details) {{
        details.addEventListener("toggle", () => {{
          if (details.open) {{
            loadResultsTable();
          }}
        }});
      }}
    }});

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

    function emptyGraphic(isEmpty, text = "暂无可展示数据") {{
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
              throw new Error("ECharts 加载失败");
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
                this.error = `无法加载课堂结果 ${{firstId}}，请从列表中选择其他结果。`;
              }}
            }}
            if (!this.error) {{
              this.error = "";
            }}
            this.$nextTick(() => this.renderCharts());
          }} catch (error) {{
            this.error = `图表加载失败：${{error}}`;
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
            statusEl.textContent = "等待选中课堂详情。";
            panelEl.textContent = "尚未加载选中课堂的详情数据。";
            return;
          }}
          statusEl.textContent = `已加载 ${{result.result_id || result.analysis_id || "选中结果"}}`;
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
        formatConfidence(value) {{
          const number = Number(value);
          if (!Number.isFinite(number)) {{
            return "未知";
          }}
          return number <= 1 ? `${{Math.round(number * 100)}}%` : `${{number.toFixed(1)}}%`;
        }},
        formatInline(value) {{
          if (value === null || value === undefined || value === "") {{
            return "未知";
          }}
          if (typeof value === "object") {{
            return JSON.stringify(value);
          }}
          return String(value);
        }},
        scoreLabel(key) {{
          return ({{
            attention: "专注",
            activity: "活跃",
            interaction: "互动",
            stage_balance: "阶段结构",
            evidence_quality: "证据质量",
            response: "响应",
            discipline: "课堂秩序"
          }})[key] || key;
        }},
        evidenceLabel(key) {{
          return ({{
            video_path_present: "视频路径",
            standardized_video_present: "标准化视频",
            keyframe_count: "关键帧数",
            audio_present: "音频",
            transcript_status: "转写状态",
            data_confidence: "数据可信度"
          }})[key] || key;
        }},
        issueLabel(issue) {{
          return issue.label || issue.tag || issue.issue_label || issue.type || issue.category || "增强问题";
        }},
        issueKey(issue) {{
          return issue.id || issue.issue_id || `${{this.issueLabel(issue)}}-${{issue.severity || "unknown"}}`;
        }},
        statusText(value) {{
          return ({{raw: "待复盘", reviewed: "已复盘", archived: "已归档"}})[value] || value || "未知";
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
          allOption.textContent = "全部班级";
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
            color: ["#2563eb", "#0fba8c"],
            animationDuration: 700,
            animationEasing: "cubicOut",
            tooltip: {{ trigger: "axis", formatter: (params) => params.map((p) => `${{p.marker}}${{p.seriesName}}：${{p.value}}`).join("<br>") }},
            legend: {{ data: ["专注度", "活跃度"] }},
            grid: {{ left: 46, right: 24, bottom: 46, top: 52 }},
            graphic: emptyGraphic(isEmpty),
            xAxis: {{
              type: "category",
              data: xAxis
            }},
            yAxis: {{ type: "value", min: 0, max: 1, axisLabel: {{ formatter: "{{value}}" }} }},
            series: [
              {{ name: "专注度", type: "line", smooth: true, symbolSize: 6, lineStyle: {{ width: 3 }}, areaStyle: {{ opacity: 0.16 }}, data: attention, markLine: {{ symbol: "none", lineStyle: {{ color: "#ea580c", type: "dashed" }}, data: [{{ yAxis: 0.6, name: "复盘阈值" }}] }} }},
              {{ name: "活跃度", type: "line", smooth: true, symbolSize: 6, lineStyle: {{ width: 3 }}, areaStyle: {{ opacity: 0.1 }}, data: activity }}
            ]
          }});
        }},
        renderStageDistribution() {{
          const stage = (this.selectedDetail && this.selectedDetail.stage_distribution) || {{}};
          const labels = [
            ["讲授", "exposition_ratio"],
            ["提问", "question_ratio"],
            ["讨论", "discussion_ratio"],
            ["总结", "summary_ratio"],
            ["课堂组织", "management_ratio"]
          ];
          const stageData = labels
            .map(([name, key]) => ({{ name, value: Number(stage[key] || 0) }}))
            .filter((item) => item.value > 0.0001);
          const isEmpty = stageData.length === 0;
          chartById("stage-distribution-chart").setOption({{
            color: ["#4f83ff", "#14b8a6", "#f59e0b", "#94a3b8", "#fb7185"],
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
          const zoneKeys = ["front", "middle", "back"];
          const zoneNames = ["前区", "中区", "后区"];
          const attentionValues = zoneKeys.map((name) => Number((zones[name] || {{}}).avg_attention_ratio || 0));
          const activityValues = zoneKeys.map((name) => Number((zones[name] || {{}}).active_ratio || 0));
          const isEmpty = attentionValues.concat(activityValues).every((value) => value === 0);
          chartById("zone-performance-chart").setOption({{
            color: ["#2563eb", "#0fba8c"],
            tooltip: {{ trigger: "axis" }},
            legend: {{ data: ["专注度", "活跃度"] }},
            grid: {{ left: 42, right: 20, bottom: 42, top: 24 }},
            graphic: emptyGraphic(isEmpty, "暂无区域表现数据"),
            xAxis: {{
              type: "category",
              data: zoneNames
            }},
            yAxis: {{ type: "value", min: 0, max: 1 }},
            series: [
              {{ name: "专注度", type: "bar", barMaxWidth: 34, itemStyle: {{ borderRadius: [8,8,0,0] }}, data: attentionValues, label: {{ show: true, position: "top", formatter: "{{c}}" }} }},
              {{ name: "活跃度", type: "bar", barMaxWidth: 34, itemStyle: {{ borderRadius: [8,8,0,0] }}, data: activityValues, label: {{ show: true, position: "top", formatter: "{{c}}" }} }}
            ]
          }});
        }},
        renderEventDistribution() {{
          const events = this.selectedEvents;
          const counts = events.reduce((acc, event) => {{
            const type = event.event_type || event.question_type || "未知事件";
            acc[type] = (acc[type] || 0) + 1;
            return acc;
          }}, {{}});
          const names = Object.keys(counts);
          chartById("event-distribution-chart").setOption({{
            color: ["#f59e0b"],
            tooltip: {{ trigger: "axis" }},
            grid: {{ left: 42, right: 20, bottom: 68, top: 24 }},
            graphic: emptyGraphic(names.length === 0, "暂无事件数据"),
            xAxis: {{ type: "category", data: names, axisLabel: {{ rotate: 25, width: 100, overflow: "truncate" }} }},
            yAxis: {{ type: "value", minInterval: 1 }},
            series: [{{
              name: "事件数",
              type: "bar",
              barMaxWidth: 42,
              itemStyle: {{ borderRadius: [8,8,0,0] }},
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
        enhanced() {{
          const detail = this.selectedDetail || {{}};
          const raw = detail.raw_payload || {{}};
          const phase32 = detail.phase32 || {{}};
          return {{
            analysis_version: detail.analysis_version || phase32.analysis_version || raw.analysis_version || "",
            algorithm_profile: detail.algorithm_profile || phase32.algorithm_profile || raw.algorithm_profile || null,
            quality_metrics: detail.quality_metrics || phase32.quality_metrics || raw.quality_metrics || {{}},
            score_breakdown: detail.score_breakdown || phase32.score_breakdown || raw.score_breakdown || {{}},
            curve_metadata: detail.curve_metadata || phase32.curve_metadata || raw.curve_metadata || {{}},
            evidence_summary: detail.evidence_summary || phase32.evidence_summary || raw.evidence_summary || {{}},
            enhanced_issues: detail.enhanced_issues || phase32.enhanced_issues || raw.enhanced_issues || []
          }};
        }},
        hasEnhanced() {{
          const enhanced = this.enhanced;
          return Boolean(
            enhanced.analysis_version ||
            Object.keys(enhanced.quality_metrics || {{}}).length ||
            Object.keys(enhanced.score_breakdown || {{}}).length ||
            Object.keys(enhanced.curve_metadata || {{}}).length ||
            Object.keys(enhanced.evidence_summary || {{}}).length ||
            (enhanced.enhanced_issues || []).length
          );
        }},
        scoreBreakdownEntries() {{
          const breakdown = this.enhanced.score_breakdown || {{}};
          return Object.entries(breakdown).map(([key, value]) => {{
            const score = typeof value === "object" && value !== null ? (value.score ?? value.value ?? value.ratio) : value;
            return {{key, label: this.scoreLabel(key), value: this.formatInline(score)}};
          }});
        }},
        evidenceSummaryEntries() {{
          const summary = this.enhanced.evidence_summary || {{}};
          return Object.entries(summary).slice(0, 8).map(([key, value]) => ({{
            key,
            label: this.evidenceLabel(key),
            value: this.formatInline(value)
          }}));
        }},
        enhancedIssuesTop() {{
          return (this.enhanced.enhanced_issues || []).slice(0, 3);
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
      statusEl.textContent = "正在加载课堂详情...";
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
        statusEl.textContent = `已加载 ${{resultId}}`;
        statusEl.className = "muted";
      }} catch (error) {{
        statusEl.textContent = "课堂详情加载失败，请检查后端服务。";
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
          statusBadge.textContent = ({{raw: "待复盘", reviewed: "已复盘", archived: "已归档"}})[status] || status;
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
          const statusText = ({{raw: "待复盘", reviewed: "已复盘", archived: "已归档"}})[status] || status;
          statusEl.textContent = `已将 ${{resultId}} 标记为：${{statusText}}。`;
          if (reloadPage) {{
            statusEl.textContent = `已将 ${{resultId}} 标记为：${{statusText}}，正在刷新列表...`;
            window.location.reload();
          }}
        }} catch (error) {{
        statusEl.textContent = "状态更新失败，请检查后端服务。";
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
    status_text = {"raw": "待复盘", "reviewed": "已复盘", "archived": "已归档"}.get(status, status)
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
        f"<td><span class=\"{status_class.strip()}\" data-result-status=\"{html.escape(analysis_id)}\">{html.escape(status_text)}</span></td>"
        f"<td><span class=\"{badge_class}\">{html.escape(source_kind)}</span></td>"
        "<td>"
        f"<button class=\"action-button\" type=\"button\" onclick=\"loadResultDetail('{html.escape(analysis_id)}')\">详情</button>"
        f"<button class=\"action-button\" type=\"button\" onclick=\"updateResultStatus('{html.escape(analysis_id)}','reviewed')\">已复盘</button>"
        f"<button class=\"action-button danger-light\" type=\"button\" onclick=\"updateResultStatus('{html.escape(analysis_id)}','archived')\">归档</button>"
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
    display_name = html.escape(str(current_user.get("display_name") or current_user.get("username") or "用户"))
    role = html.escape(role_label(str(current_user.get("role") or "")))
    return f"""
    <div class="identity" data-marker="phase29-user-identity">
      <span>{display_name} · {role}</span>
      <button class="logout" type="button" onclick="fetch('/api/auth/logout', {{method: 'POST'}}).finally(() => window.location.href='/login')">退出</button>
    </div>
    """


def _teacher_dashboard_nav(current_user: Optional[dict]) -> str:
    return f"""
    <nav class="nav" data-marker="teacher-console-nav">
      <div>
        <strong>智能课堂行为分析与教学反馈平台</strong>
        <span class="badge">教师端</span>
      </div>
      <div class="nav-links">
        <a href="/teacher">教学首页</a>
        <a href="/teacher/results">课堂记录</a>
        <a class="active" href="/dashboard">课堂分析</a>
        <a href="/teacher/trends">趋势洞察</a>
        <a href="/teacher/reports">报告中心</a>
      </div>
    </nav>
    """


def _stringify(value: Any) -> str:
    if value in (None, ""):
        return "N/A"
    return str(value)
