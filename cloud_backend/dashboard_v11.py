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
    hero_metric_rows = _hero_metric_rows(latest)

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
    .scope-note {{ margin-top: 12px; border: 1px solid #c7d2fe; background: #f8fbff; color: #334155; border-radius: 16px; padding: 12px 14px; line-height: 1.65; font-size: 13px; }}
    .scope-note strong {{ display: block; color: #1e3a8a; margin-bottom: 4px; }}
    .scope-note.warning {{ border-color: #fde68a; background: #fffbeb; }}
    .scope-note.warning strong {{ color: #92400e; }}
    .scope-note.subtle {{ border-color: #e2e8f0; background: #f8fafc; }}
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
      <p class="muted">把课堂视频证据、课堂活动、关键事件和教学建议整合到同一页，帮助教师完成有依据的复盘。</p>
      <div class="pipeline" data-marker="data-pipeline-status">
        <span>采集端或外部样本</span><span>-></span><span>本地分析</span><span>-></span><span>云端反馈</span>
      </div>
      {hero_metric_rows}
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
          <div v-if="finalSampleScopeNote" class="scope-note" data-marker="final-sample-source-note">
            <strong>样本来源说明</strong>
            <p>当前课堂样本来自 SAV 外部公开课堂视频，已由本地分析端处理并自动上传至云端；该样本用于完整课堂展示，不属于树莓派自采数据。</p>
          </div>
          <div v-if="demoPlaybackScopeNote" class="scope-note warning" data-marker="demo-playback-scope-note">
            <strong>播放链路 smoke test</strong>
            <p>该记录为播放链路 smoke test，不作为最终完整课堂分析展示样本。</p>
          </div>
          <div v-if="unsupportedMetricsScopeNote" class="scope-note subtle" data-marker="unsupported-metrics-note">
            <strong>指标口径提示</strong>
            <p v-text="displayScope.unsupported_metric_note"></p>
          </div>
        </div>
        <aside class="insight-panel insight-stack">
          <p class="section-kicker">教学洞察</p>
          <h3 v-text="asrTrustedMetricsOnly ? 'ASR 互动证据与复盘动作' : '课堂结论与复盘动作'"></h3>
          <template v-if="asrTrustedMetricsOnly">
            <div class="large-score" data-marker="asr-response-primary-score" v-text="formatPercent(asrDisplay.response_success_rate)"></div>
            <p class="muted">ASR 互动响应</p>
          </template>
          <template v-else>
            <div class="large-score" v-text="formatScore(summary.feedback_score)"></div>
            <p class="muted">综合反馈分</p>
          </template>
          <div class="feedback-box" data-marker="teaching-feedback-summary">
            <p v-text="summary.summary_text || '暂无教学反馈摘要。'"></p>
          </div>
          <div v-if="asrTrustedMetricsOnly" class="score-strip" data-marker="trusted-asr-insight-metrics">
            <div class="score-card"><span class="muted">提问候选</span><strong v-text="asrDisplay.question_event_count || 0"></strong></div>
            <div class="score-card"><span class="muted">检测到响应</span><strong v-text="asrDisplay.response_detected_count || 0"></strong></div>
            <div class="score-card"><span class="muted">事件</span><strong v-text="selectedEvents.length"></strong></div>
          </div>
          <div v-else class="score-strip">
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
      <section v-if="hasEnhanced && !asrTrustedMetricsOnly" class="card insight-card" data-marker="phase32-enhanced-summary">
        <div class="section-title">
          <div>
            <p class="section-kicker">Phase 3.2 增强解释</p>
            <h2>分析可信度 / 评分解释</h2>
            <p class="muted">本区仅在本地端上传 enhanced JSON 字段时展示；旧数据缺字段时页面保持原有展示。</p>
            <p v-if="unsupportedMetricsScopeNote" class="muted" data-marker="enhanced-unsupported-metrics-note" v-text="displayScope.unsupported_metric_note"></p>
          </div>
          <span class="badge" v-text="'analysis_version ' + (enhanced.analysis_version || '未标注')"></span>
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
        <div class="grid" v-if="scoreBreakdownEntries.length && !asrTrustedMetricsOnly">
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
      <section v-if="hasQuestionGuidance && !hasAsrQuestionCandidates" class="card insight-card" data-marker="phase33-question-guidance">
        <div class="section-title">
          <div>
            <p class="section-kicker">Phase 3.3 提问引导</p>
            <h2>教师提问与课堂引导证据</h2>
            <p class="muted">本区仅在上传 JSON 包含 teacher_question_events 或 question_guidance_summary 时展示；旧数据缺字段时不影响课堂分析。</p>
            <p v-if="unsupportedMetricsScopeNote" class="muted" data-marker="question-unsupported-metrics-note" v-text="displayScope.unsupported_metric_note"></p>
          </div>
          <span v-if="questionGuidanceDemo" class="badge sample">演示数据</span>
        </div>
        <div class="grid">
          <div class="metric">
            <span>提问数量</span>
            <strong v-text="questionGuidanceCount"></strong>
          </div>
          <div class="metric">
            <span>引导评分</span>
            <strong v-text="formatInline(questionGuidance.summary.guidance_score || questionGuidance.summary.score)"></strong>
          </div>
          <div class="metric">
            <span>响应信号</span>
            <strong v-text="formatInline(questionGuidance.summary.response_signal_summary || questionGuidance.summary.response_signal)"></strong>
          </div>
        </div>
        <div class="grid">
          <div class="record">
            <strong>开放 / 封闭 / 检查分布</strong>
            <p v-for="entry in questionDistributionEntries" :key="entry.key">
              <span class="muted" v-text="entry.label"></span>：<span v-text="entry.value"></span>
            </p>
            <p v-if="!questionDistributionEntries.length" class="muted">暂无提问类型分布。</p>
          </div>
          <div class="record">
            <strong>前 / 中 / 后覆盖</strong>
            <p v-for="entry in questionCoverageEntries" :key="entry.key">
              <span class="muted" v-text="entry.label"></span>：<span v-text="entry.value"></span>
            </p>
            <p v-if="!questionCoverageEntries.length" class="muted">暂无课堂阶段覆盖数据。</p>
          </div>
          <div class="record">
            <strong>主要问题与建议</strong>
            <p><span class="muted">问题：</span><span v-text="formatInline(questionGuidance.summary.main_issue || questionGuidance.summary.issue)"></span></p>
            <p><span class="muted">证据：</span><span v-text="formatInline(questionGuidance.summary.evidence)"></span></p>
            <p><span class="muted">建议：</span><span v-text="formatInline(questionGuidance.summary.suggestion)"></span></p>
          </div>
        </div>
        <div class="list">
          <h3>提问时间线与示例</h3>
          <div v-if="questionEventsTop.length">
            <div class="record" v-for="event in questionEventsTop" :key="questionKey(event)">
              <div class="record-head">
                <strong v-text="questionLabel(event)"></strong>
                <span class="badge" v-text="questionKindLabel(event.question_type || event.type || event.category)"></span>
              </div>
              <p><span class="muted">时间：</span><span v-text="formatInline(event.start_sec || event.time_sec || event.timestamp_sec)"></span> 秒</p>
              <p><span class="muted">学生响应：</span><span v-text="formatInline(event.response_signal || event.response || event.student_response)"></span></p>
              <p><span class="muted">引导建议：</span><span v-text="formatInline(event.guidance || event.suggestion)"></span></p>
            </div>
          </div>
          <div v-else class="empty">旧提问引导未提供独立示例；如存在 ASR 提问候选，请以课堂语音转写模块为准。</div>
        </div>
      </section>
      <section v-if="hasAsrDisplay" class="card insight-card" data-marker="phase315-asr-display">
        <div class="section-title">
          <div>
            <p class="section-kicker">Phase 3.15 ASR 展示</p>
            <h2>课堂语音转写与提问候选</h2>
            <p class="muted">展示本地 ASR 转写摘要、教师提问候选事件和视觉响应对齐统计，不展开完整转写全文。</p>
          </div>
          <span class="badge" v-text="asrDisplay.transcript_present ? '转写已生成' : '未提供转写'"></span>
        </div>
        <div class="scope-note subtle" data-marker="asr-boundary-note">
          <strong>边界说明</strong>
          <p v-text="asrDisplay.note || '提问事件基于本地 ASR 转写、规则检测与视觉响应对齐生成；当前未进行说话人分离，因此作为教师提问候选事件展示，不做精准教师身份判断。'"></p>
        </div>
        <div v-if="asrDisplay.transcript_present" class="grid" data-marker="asr-transcript-summary">
          <div class="metric">
            <span>转写片段</span>
            <strong v-text="asrDisplay.transcript_segment_count || 0"></strong>
          </div>
          <div class="metric">
            <span>提问候选</span>
            <strong v-text="asrDisplay.question_event_count || 0"></strong>
          </div>
          <div class="metric">
            <span>检测到响应</span>
            <strong v-text="asrDisplay.response_detected_count || 0"></strong>
          </div>
          <div class="metric">
            <span>响应率</span>
            <strong v-text="formatPercent(asrDisplay.response_success_rate)"></strong>
          </div>
          <div class="metric">
            <span>ASR 引擎</span>
            <strong v-text="asrDisplay.asr_engine || '未知'"></strong>
          </div>
          <div class="metric">
            <span>说话人分离</span>
            <strong v-text="asrDisplay.speaker_diarization ? '已启用' : '未启用'"></strong>
          </div>
        </div>
        <div v-else class="empty" data-marker="asr-transcript-empty">当前样本未提供课堂转写，语音相关指标仅作结构展示。</div>
        <div class="grid">
          <div class="record">
            <strong>转写片段预览</strong>
            <div v-if="asrSnippets.length">
              <p v-for="snippet in asrSnippets" :key="asrSnippetKey(snippet)">
                <span class="muted" v-text="formatTimeRange(snippet)"></span>：
                <span v-text="snippet.text"></span>
              </p>
            </div>
            <p v-else class="muted">暂无可展示转写片段。</p>
          </div>
          <div class="record" data-marker="asr-question-candidates">
            <strong>典型提问候选</strong>
            <div v-if="asrQuestionCandidates.length">
              <p v-for="event in asrQuestionCandidates" :key="asrQuestionKey(event)">
                <span class="muted" v-text="formatTimeRange(event)"></span>：
                <span v-text="event.text || '未标注文本'"></span>
                <span class="badge" v-text="event.response_detected ? '已检测到视觉响应' : '未检测到明确响应'"></span>
              </p>
            </div>
            <p v-else class="muted">暂无提问候选事件。</p>
          </div>
        </div>
      </section>
      <div class="dashboard-grid">
        <div class="chart-panel dashboard-main">
          <h3 class="chart-title" data-marker="activity-timeline-title" v-text="asrTrustedMetricsOnly ? '课堂活跃度与提问候选时间线' : '专注度 / 活跃度 / 提问候选时间线'"></h3>
          <p class="muted">主图用于定位课堂参与低谷、互动提问点和复盘重点。</p>
          <p v-if="visualLowConfidence" class="scope-note subtle" data-marker="visual-low-confidence-note">视觉侧专注度、热度和教学阶段估计在该外部样本上置信度较低；当前展示以视频证据、活跃度曲线、ASR 提问候选和响应对齐为主。</p>
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
        <div v-if="!hideStageDistribution" class="chart-panel" data-marker="stage-distribution-panel">
          <h3 class="chart-title">教学阶段分布</h3>
          <p v-if="visualStageLowConfidence" class="muted" data-marker="stage-zero-handled-note">暂无可靠教学阶段分布，当前 ASR 仅提供提问候选与响应对齐。</p>
          <div id="stage-distribution-chart" class="chart-box" data-marker="stage-distribution-chart"></div>
        </div>
        <div class="chart-panel">
          <h3 class="chart-title" v-text="hideRegionAttention ? '前 / 中 / 后区域活跃度' : '前 / 中 / 后区域表现'"></h3>
          <p v-if="zoneAttentionLowConfidence" class="muted" data-marker="zone-low-confidence-note">区域活跃度可用于观察课堂参与，专注度估计在该样本上置信度不足。</p>
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
      const element = document.getElementById(id);
      if (!element) {{
        return null;
      }}
      chartInstances[id] = echarts.init(element);
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
          if (!this.hideStageDistribution) {{
            this.renderStageDistribution();
          }} else if (chartInstances["stage-distribution-chart"]) {{
            chartInstances["stage-distribution-chart"].dispose();
            delete chartInstances["stage-distribution-chart"];
          }}
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
            display_scope: result.display_scope,
            display_flags: result.display_flags,
            asr_display: result.asr_display,
            source_dataset: result.source_dataset,
            sample_type: result.sample_type,
            is_pi_capture: result.is_pi_capture,
            is_own_capture: result.is_own_capture,
            is_final_dashboard_sample: result.is_final_dashboard_sample,
            is_demo_playback_sample: result.is_demo_playback_sample,
            raw_payload: result.raw_payload,
            phase33: result.phase33,
            teacher_question_events: result.teacher_question_events,
            question_guidance_summary: result.question_guidance_summary
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
        formatPercent(value) {{
          const number = Number(value);
          if (!Number.isFinite(number)) {{
            return "未知";
          }}
          return number <= 1 ? `${{(number * 100).toFixed(1)}}%` : `${{number.toFixed(1)}}%`;
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
        boolish(value) {{
          if (value === true || value === false) {{
            return value;
          }}
          if (value === 1 || value === 0) {{
            return Boolean(value);
          }}
          if (typeof value === "string") {{
            const normalized = value.trim().toLowerCase();
            if (["true", "1", "yes", "on"].includes(normalized)) {{
              return true;
            }}
            if (["false", "0", "no", "off"].includes(normalized)) {{
              return false;
            }}
          }}
          return null;
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
        questionKindLabel(value) {{
          return ({{
            open: "开放提问",
            closed: "封闭提问",
            check: "检查理解",
            guiding: "引导追问",
            reasoning: "推理追问"
          }})[value] || value || "未知类型";
        }},
        questionLabel(event) {{
          return event.text || event.question_text || event.prompt || event.label || event.event_id || "未标注提问";
        }},
        questionKey(event) {{
          return event.event_id || event.id || `${{this.questionLabel(event)}}-${{event.start_sec || event.time_sec || "unknown"}}`;
        }},
        asrSnippetKey(snippet) {{
          return `${{snippet.start_sec || 0}}-${{snippet.end_sec || 0}}-${{snippet.text || ""}}`;
        }},
        asrQuestionKey(event) {{
          return event.event_id || `${{event.start_sec || 0}}-${{event.text || ""}}`;
        }},
        formatTimeRange(item) {{
          const start = Number(item.start_sec || 0);
          const end = Number(item.end_sec || 0);
          const startText = Number.isFinite(start) ? start.toFixed(1) : "0.0";
          const endText = Number.isFinite(end) ? end.toFixed(1) : "";
          return endText ? `${{startText}}s-${{endText}}s` : `${{startText}}s`;
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
          const showAttention = !this.hideAttentionCurve;
          const maxLength = Math.max(showAttention ? attention.length : 0, activity.length, 1);
          const xAxis = Array.from({{length: maxLength}}, (_, index) => `${{Math.round(index * windowSize)}}s`);
          const isEmpty = !activity.length && (!showAttention || !attention.length);
          const attentionAllZero = attention.length > 0 && attention.every((value) => Number(value || 0) === 0);
          const activityAvailable = activity.some((value) => Number(value || 0) > 0);
          const questionMarkers = this.selectedEvents
            .filter((event) => event.event_type === "question_candidate" || event.question_type === "question_candidate")
            .map((event) => {{
              const index = Math.max(0, Math.min(maxLength - 1, Math.round(Number(event.start_sec || 0) / windowSize)));
              return [index, 0.92, event.text || "提问候选"];
            }});
          const series = [];
          if (showAttention) {{
            series.push({{ name: "专注度", type: "line", smooth: true, symbolSize: 6, lineStyle: {{ width: 3 }}, areaStyle: {{ opacity: 0.16 }}, data: attention, markLine: {{ symbol: "none", lineStyle: {{ color: "#ea580c", type: "dashed" }}, data: [{{ yAxis: 0.6, name: "复盘阈值" }}] }} }});
          }}
          series.push({{ name: "活跃度", type: "line", smooth: true, symbolSize: 6, lineStyle: {{ width: 3 }}, areaStyle: {{ opacity: 0.1 }}, data: activity }});
          series.push({{ name: "提问候选", type: "scatter", symbolSize: 10, data: questionMarkers, tooltip: {{ valueFormatter: (value) => Array.isArray(value) ? value[2] : value }} }});
          const chart = chartById("attention-activity-chart");
          if (!chart) {{
            return;
          }}
          chart.setOption({{
            color: showAttention ? ["#2563eb", "#0fba8c", "#f59e0b"] : ["#0fba8c", "#f59e0b"],
            animationDuration: 700,
            animationEasing: "cubicOut",
            tooltip: {{ trigger: "axis", formatter: (params) => params.map((p) => `${{p.marker}}${{p.seriesName}}：${{p.value}}`).join("<br>") }},
            legend: {{ data: showAttention ? ["专注度", "活跃度", "提问候选"] : ["活跃度", "提问候选"] }},
            grid: {{ left: 46, right: 24, bottom: 46, top: 52 }},
            graphic: emptyGraphic(isEmpty, "暂无时间线数据") || (attentionAllZero && activityAvailable ? {{
              type: "text",
              right: 24,
              top: 18,
              style: {{ text: "视觉专注/热度数据不足，活跃度曲线可用于复盘。", fill: "#64748b", fontSize: 12, fontWeight: 700 }}
            }} : null),
            xAxis: {{
              type: "category",
              data: xAxis
            }},
            yAxis: {{ type: "value", min: 0, max: 1, axisLabel: {{ formatter: "{{value}}" }} }},
            series
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
          const chart = chartById("stage-distribution-chart");
          if (!chart) {{
            return;
          }}
          chart.setOption({{
            color: ["#4f83ff", "#14b8a6", "#f59e0b", "#94a3b8", "#fb7185"],
            tooltip: {{ trigger: "item" }},
            legend: {{ bottom: 0, type: "scroll" }},
            graphic: emptyGraphic(isEmpty, "暂无可靠教学阶段分布，当前 ASR 仅提供提问候选与响应对齐。"),
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
          const showAttention = !this.hideRegionAttention;
          const isEmpty = (showAttention ? attentionValues.concat(activityValues) : activityValues).every((value) => value === 0);
          const attentionAllZero = attentionValues.every((value) => value === 0);
          const activityAvailable = activityValues.some((value) => value > 0);
          const series = [];
          if (showAttention) {{
            series.push({{ name: "专注度", type: "bar", barMaxWidth: 34, itemStyle: {{ borderRadius: [8,8,0,0] }}, data: attentionValues, label: {{ show: true, position: "top", formatter: "{{c}}" }} }});
          }}
          series.push({{ name: "活跃度", type: "bar", barMaxWidth: 34, itemStyle: {{ borderRadius: [8,8,0,0] }}, data: activityValues, label: {{ show: true, position: "top", formatter: "{{c}}" }} }});
          const chart = chartById("zone-performance-chart");
          if (!chart) {{
            return;
          }}
          chart.setOption({{
            color: showAttention ? ["#2563eb", "#0fba8c"] : ["#0fba8c"],
            tooltip: {{ trigger: "axis" }},
            legend: {{ data: showAttention ? ["专注度", "活跃度"] : ["活跃度"] }},
            grid: {{ left: 42, right: 20, bottom: 42, top: 24 }},
            graphic: emptyGraphic(isEmpty, "暂无区域表现数据") || (attentionAllZero && activityAvailable ? {{
              type: "text",
              left: "center",
              top: 12,
              style: {{ text: "活跃度可用，专注度估计不足", fill: "#64748b", fontSize: 12, fontWeight: 700 }}
            }} : null),
            xAxis: {{
              type: "category",
              data: zoneNames
            }},
            yAxis: {{ type: "value", min: 0, max: 1 }},
            series
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
          const chart = chartById("event-distribution-chart");
          if (!chart) {{
            return;
          }}
          chart.setOption({{
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
        asrDisplay() {{
          const detail = this.selectedDetail || {{}};
          const raw = detail.raw_payload || {{}};
          const audio = raw.audio || {{}};
          const evidence = raw.evidence_summary || {{}};
          const summary = raw.summary || {{}};
          const asrQuality = raw.asr_quality || {{}};
          const explicit = detail.asr_display || raw.asr_display || {{}};
          const transcript = Array.isArray(raw.transcript) ? raw.transcript : [];
          const teacher = raw.teacher || {{}};
          const rawQuestions = Array.isArray(teacher.question_events) ? teacher.question_events : (Array.isArray(raw.teacher_question_events) ? raw.teacher_question_events : []);
          const alignment = Array.isArray(raw.interaction_alignment) ? raw.interaction_alignment : [];
          const responseById = alignment.reduce((acc, item) => {{
            const id = item.question_event_id || item.event_id;
            if (id) {{
              acc[id] = item;
            }}
            return acc;
          }}, {{}});
          const questionEvents = Array.isArray(explicit.question_events) && explicit.question_events.length
            ? explicit.question_events
            : rawQuestions.slice(0, 5).map((event) => {{
              const aligned = responseById[event.event_id] || {{}};
              return {{
                event_id: event.event_id,
                start_sec: event.start_sec,
                end_sec: event.end_sec,
                text: event.text,
                confidence: event.confidence,
                response_detected: Boolean(aligned.response_detected)
              }};
            }});
          const snippets = Array.isArray(explicit.snippets) && explicit.snippets.length
            ? explicit.snippets
            : transcript.filter((segment) => segment && segment.text).slice(0, 8).map((segment) => ({{
              start_sec: segment.start_sec,
              end_sec: segment.end_sec,
              text: segment.text
            }}));
          const questionCount = Number(explicit.question_event_count ?? summary.teacher_question_count ?? rawQuestions.length ?? 0);
          const responseDetected = Number(explicit.response_detected_count ?? alignment.filter((item) => item.response_detected === true).length ?? 0);
          const rate = explicit.response_success_rate ?? summary.response_success_rate ?? (questionCount ? responseDetected / questionCount : 0);
          const transcriptPresent = this.boolish(explicit.transcript_present ?? audio.transcript_present ?? evidence.transcript_present ?? raw.has_asr_transcript) === true || transcript.length > 0;
          return {{
            transcript_present: transcriptPresent,
            transcript_segment_count: Number(explicit.transcript_segment_count ?? audio.transcript_segment_count ?? evidence.transcript_segment_count ?? transcript.length ?? 0),
            asr_engine: explicit.asr_engine || audio.asr_engine || "",
            question_event_count: questionCount,
            alignment_count: Number(explicit.alignment_count ?? alignment.length ?? 0),
            response_detected_count: responseDetected,
            response_success_rate: rate,
            speaker_diarization: this.boolish(explicit.speaker_diarization ?? asrQuality.speaker_diarization) === true,
            teacher_identity_confidence: explicit.teacher_identity_confidence || asrQuality.teacher_identity_confidence || "low_without_diarization",
            snippets,
            question_events: questionEvents,
            note: explicit.note || asrQuality.note || (transcriptPresent
              ? "提问事件基于本地 ASR 转写、规则检测与视觉响应对齐生成；当前未进行说话人分离，因此作为教师提问候选事件展示，不做精准教师身份判断。"
              : "当前样本未提供课堂转写，语音相关指标仅作结构展示。")
          }};
        }},
        hasAsrDisplay() {{
          const raw = (this.selectedDetail && this.selectedDetail.raw_payload) || {{}};
          const display = this.asrDisplay;
          return Boolean(this.selectedDetail && (
            this.selectedDetail.asr_display ||
            raw.has_asr_transcript ||
            raw.has_question_events ||
            raw.has_visual_response_alignment ||
            display.transcript_present ||
            display.question_event_count ||
            display.alignment_count
          ));
        }},
        asrSnippets() {{
          return (this.asrDisplay.snippets || []).slice(0, 8);
        }},
        asrQuestionCandidates() {{
          return (this.asrDisplay.question_events || []).slice(0, 5);
        }},
        displayScope() {{
          const detail = this.selectedDetail || {{}};
          const raw = detail.raw_payload || {{}};
          const source = raw.source || {{}};
          const capture = raw.capture || {{}};
          const video = raw.video || {{}};
          const evidence = raw.evidence_summary || {{}};
          const phase37 = raw.phase37_final_dashboard_sample || {{}};
          const explicit = detail.display_scope || raw.display_scope || {{}};
          const sourceDataset = explicit.source_dataset || detail.source_dataset || raw.source_dataset || capture.source_dataset || source.source_dataset || "";
          const sampleType = explicit.sample_type || detail.sample_type || raw.sample_type || capture.sample_type || video.sample_type || "";
          const isPiCapture = this.boolish(explicit.is_pi_capture ?? detail.is_pi_capture ?? raw.is_pi_capture ?? capture.is_pi_capture ?? source.is_pi_capture);
          const isOwnCapture = this.boolish(explicit.is_own_capture ?? detail.is_own_capture ?? raw.is_own_capture ?? capture.is_own_capture ?? source.is_own_capture);
          const isDemo = this.boolish(explicit.is_demo_playback_sample ?? detail.is_demo_playback_sample ?? raw.is_demo_playback_sample ?? capture.is_demo_playback_sample ?? video.is_demo_playback_sample) === true
            || String(sampleType).includes("cloud_playback_demo");
          const isFinal = this.boolish(explicit.is_final_dashboard_sample ?? detail.is_final_dashboard_sample ?? raw.is_final_dashboard_sample ?? capture.is_final_dashboard_sample ?? video.is_final_dashboard_sample ?? phase37.final_dashboard_sample) === true;
          const audioPresent = this.boolish(raw.audio_present ?? evidence.audio_present);
          const transcriptPresent = this.boolish(raw.transcript_present ?? evidence.transcript_present);
          const questionEvents = raw.teacher_question_events || (raw.teacher && raw.teacher.question_events) || [];
          const questionSummary = raw.question_guidance_summary || {{}};
          return Object.assign({{}}, explicit, {{
            source_dataset: sourceDataset,
            source_label: explicit.source_label || (String(sourceDataset).toUpperCase() === "SAV" ? "SAV 外部公开课堂视频" : sourceDataset),
            sample_type: sampleType,
            is_pi_capture: isPiCapture,
            is_own_capture: isOwnCapture,
            is_demo_playback_sample: isDemo,
            is_final_dashboard_sample: isFinal,
            unsupported_metric_note: explicit.unsupported_metric_note || (
              String(sourceDataset).toUpperCase() === "SAV" && (audioPresent === false || transcriptPresent === false || !questionEvents.length || questionSummary.source === "teacher_transcript_empty")
                ? "该外部视频样本未提供有效课堂转写或提问证据，语音相关教学阶段和教师提问指标仅作结构展示，不作为主要评价依据。"
                : ""
            ),
            no_sav50_mixed: Boolean(explicit.no_sav50_mixed || phase37.not_sav50_composite || isFinal)
          }});
        }},
        finalSampleScopeNote() {{
          const scope = this.displayScope;
          return Boolean(scope.is_final_dashboard_sample && String(scope.source_dataset || "").toUpperCase() === "SAV" && scope.is_pi_capture === false && scope.is_own_capture === false);
        }},
        demoPlaybackScopeNote() {{
          const scope = this.displayScope;
          return Boolean(scope.is_demo_playback_sample || String(scope.sample_type || "").includes("cloud_playback_demo"));
        }},
        unsupportedMetricsScopeNote() {{
          return Boolean(this.displayScope.unsupported_metric_note);
        }},
        displayFlags() {{
          const detail = this.selectedDetail || {{}};
          const explicit = detail.display_flags || {{}};
          const sampleType = this.displayScope.sample_type || detail.sample_type || "";
          const sourceDataset = String(this.displayScope.source_dataset || detail.source_dataset || "").toUpperCase();
          const asrTrusted = Boolean(
            explicit.asr_trusted_metrics_only ||
            (this.asrDisplay.transcript_present && Number(this.asrDisplay.question_event_count || 0) > 0 &&
              (sampleType === "external_full_classroom_video_with_asr" || sourceDataset === "SAV"))
          );
          return Object.assign({{}}, explicit, {{
            asr_trusted_metrics_only: asrTrusted,
            hide_attention_metrics: explicit.hide_attention_metrics ?? asrTrusted,
            hide_avg_attention: explicit.hide_avg_attention ?? asrTrusted,
            hide_attention_curve: explicit.hide_attention_curve ?? asrTrusted,
            hide_region_attention: explicit.hide_region_attention ?? asrTrusted,
            hide_student_count: explicit.hide_student_count ?? asrTrusted,
            hide_stage_distribution: explicit.hide_stage_distribution ?? (asrTrusted && this.visualStageLowConfidence),
            hide_phase32_score_breakdown: explicit.hide_phase32_score_breakdown ?? asrTrusted,
            hide_feedback_score_as_primary: explicit.hide_feedback_score_as_primary ?? asrTrusted
          }});
        }},
        asrTrustedMetricsOnly() {{
          return Boolean(this.displayFlags.asr_trusted_metrics_only);
        }},
        hideAttentionCurve() {{
          return Boolean(this.displayFlags.hide_attention_curve);
        }},
        hideRegionAttention() {{
          return Boolean(this.displayFlags.hide_region_attention);
        }},
        hideStageDistribution() {{
          return Boolean(this.displayFlags.hide_stage_distribution);
        }},
        hidePhase32ScoreBreakdown() {{
          return Boolean(this.displayFlags.hide_phase32_score_breakdown);
        }},
        visualLowConfidence() {{
          const timeline = (this.selectedDetail && this.selectedDetail.timeline) || {{}};
          const attention = timeline.attention_curve || [];
          const heat = timeline.heat_curve || [];
          return this.visualStageLowConfidence
            && attention.length > 0
            && heat.length > 0
            && attention.every((value) => Number(value || 0) === 0)
            && heat.every((value) => Number(value || 0) === 0);
        }},
        visualStageLowConfidence() {{
          const stage = (this.selectedDetail && this.selectedDetail.stage_distribution) || {{}};
          const values = Object.values(stage).map((value) => Number(value || 0));
          return values.length > 0 && values.every((value) => value === 0);
        }},
        zoneAttentionLowConfidence() {{
          const zones = (this.selectedDetail && this.selectedDetail.zones) || {{}};
          const zoneKeys = ["front", "middle", "back"];
          const attentionValues = zoneKeys.map((name) => Number((zones[name] || {{}}).avg_attention_ratio || 0));
          const activityValues = zoneKeys.map((name) => Number((zones[name] || {{}}).active_ratio || 0));
          return attentionValues.every((value) => value === 0) && activityValues.some((value) => value > 0);
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
          if (this.asrTrustedMetricsOnly) {{
            return false;
          }}
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
          if (this.hidePhase32ScoreBreakdown) {{
            return [];
          }}
          const breakdown = this.enhanced.score_breakdown || {{}};
          return Object.entries(breakdown).map(([key, value]) => {{
            const score = typeof value === "object" && value !== null ? (value.score ?? value.value ?? value.ratio) : value;
            return {{key, label: this.scoreLabel(key), value: this.formatInline(score)}};
          }});
        }},
        evidenceSummaryEntries() {{
          const summary = this.enhanced.evidence_summary || {{}};
          const hiddenForAsr = new Set(["audio_present", "audio", "detected_student_count_avg", "keyframe_count"]);
          return Object.entries(summary)
            .filter(([key]) => !(this.asrTrustedMetricsOnly && hiddenForAsr.has(key)))
            .slice(0, 8).map(([key, value]) => ({{
            key,
            label: this.evidenceLabel(key),
            value: this.formatInline(value)
          }}));
        }},
        enhancedIssuesTop() {{
          if (this.asrTrustedMetricsOnly) {{
            return [];
          }}
          return (this.enhanced.enhanced_issues || []).slice(0, 3);
        }},
        questionGuidance() {{
          const detail = this.selectedDetail || {{}};
          const raw = detail.raw_payload || {{}};
          const phase33 = detail.phase33 || {{}};
          const summary = detail.question_guidance_summary || phase33.question_guidance_summary || raw.question_guidance_summary || {{}};
          const events = detail.teacher_question_events || phase33.teacher_question_events || raw.teacher_question_events || [];
          return {{
            summary: summary || {{}},
            events: Array.isArray(events) ? events : []
          }};
        }},
        hasQuestionGuidance() {{
          const guidance = this.questionGuidance;
          return Boolean((guidance.events || []).length || Object.keys(guidance.summary || {{}}).length);
        }},
        hasAsrQuestionCandidates() {{
          return Boolean(this.asrDisplay && Number(this.asrDisplay.question_event_count || 0) > 0);
        }},
        questionGuidanceCount() {{
          const summary = this.questionGuidance.summary || {{}};
          return summary.question_count || summary.teacher_question_count || (this.questionGuidance.events || []).length || 0;
        }},
        questionGuidanceDemo() {{
          const detail = this.selectedDetail || {{}};
          const raw = detail.raw_payload || {{}};
          const dataset = raw.dataset || {{}};
          const summary = this.questionGuidance.summary || {{}};
          return [detail.status, dataset.source, summary.source, summary.status].some((value) => value === "demo" || value === "demo_seed");
        }},
        questionDistributionEntries() {{
          const summary = this.questionGuidance.summary || {{}};
          const distribution = summary.question_distribution || summary.open_closed_check_distribution || summary.distribution || {{}};
          return Object.entries(distribution).map(([key, value]) => ({{
            key,
            label: this.questionKindLabel(key),
            value: this.formatInline(value)
          }}));
        }},
        questionCoverageEntries() {{
          const summary = this.questionGuidance.summary || {{}};
          const coverage = summary.stage_coverage || summary.coverage || summary.early_middle_late_coverage || {{}};
          const labels = {{early: "前段", middle: "中段", late: "后段"}};
          return Object.entries(coverage).map(([key, value]) => ({{
            key,
            label: labels[key] || key,
            value: this.formatInline(value)
          }}));
        }},
        questionEventsTop() {{
          const summary = this.questionGuidance.summary || {{}};
          const examples = summary.top_examples || summary.examples || [];
          const source = (Array.isArray(examples) && examples.length) ? examples : this.questionGuidance.events;
          return (source || []).slice(0, 5);
        }},
        summary() {{
          return (this.selectedDetail && this.selectedDetail.summary) || {{}};
        }},
        selectedEvents() {{
          const events = (this.selectedDetail && this.selectedDetail.events) || [];
          if (events.length) {{
            return events;
          }}
          return (this.asrDisplay.question_events || []).map((event, index) => Object.assign({{
            event_id: event.event_id || `question_candidate_${{index + 1}}`,
            event_type: "question_candidate",
            question_type: "question_candidate"
          }}, event));
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
          display_scope: result.display_scope,
          display_flags: result.display_flags,
          asr_display: result.asr_display,
          source_dataset: result.source_dataset,
          sample_type: result.sample_type,
          is_pi_capture: result.is_pi_capture,
          is_own_capture: result.is_own_capture,
          is_final_dashboard_sample: result.is_final_dashboard_sample,
          is_demo_playback_sample: result.is_demo_playback_sample,
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


def _metric_card(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f'<span class="metric-label">{html.escape(label)}</span>'
        f'<div class="metric-value">{html.escape(_stringify(value))}</div>'
        "</div>"
    )


def _hero_metric_rows(latest: dict[str, Any]) -> str:
    trusted_only = bool((latest.get("display_flags") or {}).get("asr_trusted_metrics_only"))
    if trusted_only:
        rows = [
            [
                ("班级", latest.get("classroom_id")),
                ("来源主机", latest.get("source_host")),
                ("生成时间", latest.get("generated_at")),
                ("教师提问候选", _number(latest.get("teacher_question_count"))),
                ("响应度", _score(latest.get("response_score"))),
                ("转写片段", _number(latest.get("transcript_segment_count"))),
            ],
            [
                ("响应成功率", _ratio(latest.get("response_success_rate"))),
                ("检测到响应", _number(latest.get("response_detected_count"))),
                ("视觉响应对齐", _number(latest.get("alignment_count"))),
                ("举手事件", _number(latest.get("hand_raise_event_count"))),
                ("分析窗口", f"{_number(latest.get('window_size_seconds'))}s"),
                ("ASR 引擎", latest.get("asr_engine") or "未知"),
            ],
        ]
    else:
        rows = [
            [
                ("班级", latest.get("classroom_id")),
                ("来源主机", latest.get("source_host")),
                ("生成时间", latest.get("generated_at")),
                ("反馈分", _score(latest.get("feedback_score"))),
                ("专注度", _score(latest.get("attention_score"))),
                ("响应度", _score(latest.get("response_score"))),
            ],
            [
                ("教师提问", _number(latest.get("teacher_question_count"))),
                ("平均专注率", _ratio(latest.get("avg_attention_ratio"))),
                ("响应成功率", _ratio(latest.get("response_success_rate"))),
                ("学生人数估计", _number(latest.get("estimated_student_count"))),
                ("举手事件", _number(latest.get("hand_raise_event_count"))),
                ("分析窗口", f"{_number(latest.get('window_size_seconds'))}s"),
            ],
        ]
    return "".join(
        '<div class="metrics">' + "".join(_metric_card(label, value) for label, value in row) + "</div>"
        for row in rows
    )


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source") or {}
    time_info = payload.get("time") or {}
    summary = payload.get("summary") or {}
    teacher = payload.get("teacher") or {}
    students = payload.get("students") or {}
    timeline = payload.get("timeline") or {}
    transcript = payload.get("transcript") or []
    question_events = teacher.get("question_events") or payload.get("teacher_question_events") or []
    alignment = payload.get("interaction_alignment") or []
    response_detected_count = len([item for item in alignment if isinstance(item, dict) and item.get("response_detected") is True])
    evidence = payload.get("evidence_summary") or {}
    audio = payload.get("audio") or {}
    capture = payload.get("capture") or {}
    video = payload.get("video") or {}
    source_dataset = _stringify(payload.get("source_dataset") or capture.get("source_dataset") or source.get("source_dataset"))
    sample_type = _stringify(payload.get("sample_type") or capture.get("sample_type") or video.get("sample_type"))
    attention_curve = timeline.get("attention_curve") or []
    heat_curve = timeline.get("heat_curve") or []
    stage_distribution = payload.get("stage_distribution") or teacher.get("stage_distribution") or {}
    asr_trusted_metrics_only = bool(
        transcript
        and question_events
        and (sample_type == "external_full_classroom_video_with_asr" or source_dataset.upper() == "SAV")
    )
    asr_summary_text = ""
    if transcript and question_events:
        asr_summary_text = (
            f"本节课已完成本地 ASR 转写，生成 {len(transcript)} 个转写片段，"
            f"识别出 {len(question_events)} 个教师提问候选事件，并完成 {len(alignment)} 条视觉响应对齐，"
            f"其中 {response_detected_count} 条检测到学生响应。由于当前未进行说话人分离，提问事件作为候选结果展示。"
        )
    display_flags = {
        "asr_trusted_metrics_only": asr_trusted_metrics_only,
        "hide_attention_metrics": asr_trusted_metrics_only and bool(attention_curve) and all(float(value or 0) == 0 for value in attention_curve),
        "hide_avg_attention": asr_trusted_metrics_only,
        "hide_student_count": asr_trusted_metrics_only and float(students.get("estimated_student_count") or 0) == 0,
        "hide_stage_distribution": asr_trusted_metrics_only and bool(stage_distribution) and all(float(value or 0) == 0 for value in stage_distribution.values()),
        "hide_phase32_score_breakdown": asr_trusted_metrics_only,
        "hide_region_attention": asr_trusted_metrics_only,
        "hide_attention_curve": asr_trusted_metrics_only and bool(attention_curve) and all(float(value or 0) == 0 for value in attention_curve),
    }
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
        "teacher_question_count": summary.get("teacher_question_count") or len(question_events),
        "avg_attention_ratio": summary.get("avg_attention_ratio"),
        "response_success_rate": summary.get("response_success_rate"),
        "summary_text": asr_summary_text or summary.get("summary_text"),
        "question_events": question_events,
        "stage_distribution": stage_distribution,
        "estimated_student_count": students.get("estimated_student_count"),
        "hand_raise_event_count": students.get("hand_raise_event_count"),
        "zones": students.get("zones") or {},
        "window_size_seconds": timeline.get("window_size_seconds"),
        "attention_curve": attention_curve,
        "heat_curve": heat_curve,
        "activity_curve": timeline.get("activity_curve") or [],
        "transcript_segment_count": audio.get("transcript_segment_count") or evidence.get("transcript_segment_count") or len(transcript),
        "alignment_count": len(alignment),
        "response_detected_count": response_detected_count,
        "asr_engine": audio.get("asr_engine") or "",
        "source_dataset": source_dataset,
        "sample_type": sample_type,
        "display_flags": display_flags,
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
        <a href="/teacher/reports">报告中心</a>
      </div>
    </nav>
    """


def _stringify(value: Any) -> str:
    if value in (None, ""):
        return "N/A"
    return str(value)
