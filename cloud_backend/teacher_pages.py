"""Teacher-facing pages polished for Phase 3.1."""
from __future__ import annotations

from typing import Optional

from .ui_style import PHASE31_STYLE, role_label


def _identity_bar(current_user: Optional[dict]) -> str:
    if not current_user:
        return ""
    display_name = current_user.get("display_name") or current_user.get("username") or "用户"
    role = role_label(current_user.get("role") or "")
    return f"""
      <div class="identity" data-marker="phase29-user-identity">
        <span>{display_name} · {role}</span>
        <button class="logout" type="button" onclick="fetch('/api/auth/logout', {{method:'POST'}}).finally(() => window.location.href='/login')">退出</button>
      </div>
    """


def _teacher_nav(active: str, current_user: Optional[dict] = None) -> str:
    active_class = {
        "home": "active" if active == "home" else "",
        "results": "active" if active == "results" else "",
        "detail": "active" if active == "detail" else "",
        "reports": "active" if active == "reports" else "",
    }
    return f"""
    <nav class="nav" data-marker="teacher-console-nav">
      <div>
        <strong>智能课堂行为分析与教学反馈平台</strong>
        <span class="badge">教师端</span>
      </div>
      <div class="nav-links">
        <a class="{active_class['home']}" href="/teacher">教学首页</a>
        <a class="{active_class['results']}" href="/teacher/results">课堂记录</a>
        <a class="{active_class['detail']}" href="/dashboard">课堂分析</a>
        <a class="{active_class['reports']}" href="/teacher/reports">报告中心</a>
      </div>
      {_identity_bar(current_user)}
    </nav>
    """


def _shell(title: str, active: str, marker: str, body: str, current_user: Optional[dict] = None) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  {PHASE31_STYLE}
</head>
<body>
  <div class="page" data-marker="{marker}">
    {_teacher_nav(active, current_user)}
    <main class="page-main">
      {body}
    </main>
  </div>
</body>
</html>"""


def build_teacher_home_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="dashboard-grid">
      <div class="page-header dashboard-main">
        <p class="kicker">教学反馈工作台</p>
        <h1 id="welcome-title">教学反馈工作台</h1>
        <p class="muted">把课堂证据、分析报告和改进建议聚合到一个工作台，先看需要复盘的课堂，再进入课堂分析和报告中心。</p>
        <p class="muted">最近数据更新：<span id="last-update">加载中...</span></p>
        <div class="action-row">
          <a class="button" href="/teacher/reports">查看课堂报告</a>
          <a class="button secondary" href="/dashboard">进入课堂分析</a>
        </div>
      </div>
      <aside class="insight-panel dashboard-side">
        <p class="kicker">复盘 Spotlight</p>
        <h2>优先处理教学行动</h2>
        <div id="todo-items" class="list" data-marker="teacher-home-todos"></div>
      </aside>
    </section>
    <p id="page-error" class="error"></p>
    <section class="grid" id="metric-grid" data-marker="teacher-home-metrics"></section>
    <section class="dashboard-grid">
      <div class="card">
        <h2>最近课堂分析</h2>
        <div id="latest-results" class="list" data-marker="teacher-home-latest"></div>
      </div>
      <div class="action-card">
        <h2>教学节奏提示</h2>
        <p class="muted">当前演示以课堂分析页和报告中心为主，优先查看视频证据、ASR 提问候选和响应对齐。</p>
        <a class="button secondary" href="/teacher/reports">查看课堂报告</a>
      </div>
    </section>
    <section class="card">
      <h2>班级概览</h2>
      <div id="classroom-summaries" class="grid" data-marker="teacher-home-classrooms"></div>
    </section>
    <script>
      const metricLabels = {
        classroom_count: "班级数",
        total_result_count: "已分析课堂",
        recent_result_count: "近期课堂",
        raw_count: "待复盘课堂",
        reviewed_count: "已复盘课堂",
        archived_count: "已归档",
        avg_feedback_score: "平均反馈",
        avg_attention_score: "平均专注",
        avg_response_score: "平均响应"
      };
      const text = (value, fallback = "暂无") => value === null || value === undefined || value === "" ? fallback : value;
      const statusLabel = (status) => ({raw:"待复盘", reviewed:"已复盘", archived:"已归档"}[status] || status || "待复盘");
      const statusBadge = (status) => `<span class="badge ${status || "raw"}">${statusLabel(status)}</span>`;
      const sampleBadge = (item) => item && item.display_badge ? `<span class="badge sample">${text(item.display_badge)}</span>` : "";
      const metricLine = (item) => {
        const metrics = (item && item.display_metrics) || [];
        return metrics.length ? metrics.map((m) => `${text(m.label)} ${text(m.value)}${m.suffix || ""}`).join(" · ") : text((item && item.data_quality_note), "暂无可信指标");
      };      async function loadTeacherHome() {
        try {
          const response = await fetch("/api/teacher/overview");
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const teacher = payload.teacher || {};
          const metrics = payload.metrics || {};
          const latest = payload.latest_results || [];
          document.getElementById("welcome-title").textContent = `欢迎回来，${teacher.display_name || teacher.username || "教师"}`;
          document.getElementById("last-update").textContent = latest[0]?.created_at || latest[0]?.generated_at || "暂无课堂数据";
          document.getElementById("metric-grid").innerHTML = Object.entries(metricLabels).filter(([key]) => metrics[key] !== null && metrics[key] !== undefined).map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(metrics[key], 0)}</strong></div>`).join("");
          document.getElementById("latest-results").innerHTML = latest.length ? latest.map((item) => `
            <div class="record">
              <div class="record-head"><strong>${text(item.lesson_title, "未命名课堂")}</strong>${sampleBadge(item)}${statusBadge(item.status)}</div>
              <p class="muted">${text(item.classroom_name)} · ${text(item.created_at || item.generated_at)}</p>
              <p>${metricLine(item)}</p>
              <a class="button secondary" href="${item.detail_url}">进入课堂分析</a>
            </div>`).join("") : `<div class="empty">暂无课堂分析，请先完成本地分析上传。</div>`;
          const todos = payload.todo_items || [];
          document.getElementById("todo-items").innerHTML = todos.length ? todos.map((item) => `
            <a class="record" href="${item.target_url || "/teacher/results"}" style="text-decoration:none;color:inherit">
              <strong>${text(item.title, "待复盘课堂")}</strong>
              <p class="muted">${text(item.description, "建议查看课堂报告并确认改进动作。")}</p>
            </a>`).join("") : `<div class="empty">暂无待处理提醒。</div>`;
          const classrooms = payload.classroom_summaries || [];
          document.getElementById("classroom-summaries").innerHTML = classrooms.length ? classrooms.map((item) => `
            <div class="record">
              <strong>${text(item.classroom_name)}</strong>
              <p class="muted">${item.result_count || 0} 节课堂 · 最近 ${text(item.latest_result_at)}</p>
              <p>平均反馈：${text(item.avg_feedback_score)}</p>
              <a class="button secondary" href="${item.records_url}">查看课堂记录</a>
            </div>`).join("") : `<div class="empty">暂无班级概览数据。</div>`;
        } catch (error) {
          document.getElementById("page-error").textContent = `教学首页加载失败：${error}`;
        }
      }
      loadTeacherHome();
    </script>
    """
    return _shell("教学反馈工作台", "home", "teacher-home-page", body, current_user)


def build_teacher_results_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">课堂记录</p>
      <h1>课堂记录中心</h1>
      <p class="muted">按班级、复盘状态和时间范围查找课堂结果，进入单堂课堂分析或报告中心。</p>
    </section>
    <section class="card">
      <form id="filters" class="filters" data-marker="teacher-results-filters">
        <div><label for="classroom_id">班级</label><select id="classroom_id" name="classroom_id"><option value="">全部班级</option></select></div>
        <div><label for="status">状态</label><select id="status" name="status"><option value="">全部状态</option><option value="raw">待复盘</option><option value="reviewed">已复盘</option><option value="archived">已归档</option></select></div>
        <div><label for="days">时间范围</label><select id="days" name="days"><option value="7">近7天</option><option value="30">近30天</option><option value="all">全部</option></select></div>
        <div><label for="limit">数量</label><input id="limit" name="limit" type="number" min="1" max="100" value="20" /></div>
        <button class="button" type="submit">筛选</button>
      </form>
    </section>
    <p id="page-error" class="error"></p>
    <section class="card">
      <h2>课堂记录 <span class="muted" id="total-count"></span></h2>
      <div id="records" data-marker="teacher-results-list"></div>
    </section>
    <script>
      const text = (value, fallback = "暂无") => value === null || value === undefined || value === "" ? fallback : value;
      const statusLabel = (status) => ({raw:"待复盘", reviewed:"已复盘", archived:"已归档"}[status] || status || "待复盘");
      const statusBadge = (status) => `<span class="badge ${status || "raw"}">${statusLabel(status)}</span>`;
      const sampleBadge = (item) => item && item.display_badge ? `<span class="badge sample">${text(item.display_badge)}</span>` : "";
      const metricCards = (item) => {
        const metrics = (item && item.display_metrics) || [];
        return metrics.length ? metrics.map((m) => `<div class="mini-stat"><span>${text(m.label)}</span><strong>${text(m.value)}${m.suffix || ""}</strong></div>`).join("") : `<div class="mini-stat"><span>指标</span><strong>暂无</strong></div>`;
      };      const currentParams = () => new URLSearchParams(window.location.search);
      function applyParamsToForm() { const params = currentParams(); ["classroom_id", "status", "days", "limit"].forEach((key) => { const el = document.getElementById(key); if (el && params.has(key)) el.value = params.get(key); }); }
      async function loadClassrooms() {
        const response = await fetch("/api/teacher/classrooms");
        if (!response.ok) throw new Error(`classrooms HTTP ${response.status}`);
        const payload = await response.json();
        const select = document.getElementById("classroom_id");
        const current = currentParams().get("classroom_id") || "";
        (payload.items || []).forEach((item) => {
          const option = document.createElement("option");
          option.value = item.classroom_id || "";
          option.textContent = item.classroom_name || item.classroom_id || "未知班级";
          option.selected = option.value === current;
          select.appendChild(option);
        });
      }
      async function loadRecords() {
        const params = currentParams();
        if (!params.has("limit")) params.set("limit", document.getElementById("limit").value || "20");
        const response = await fetch(`/api/teacher/results?${params.toString()}`);
        if (!response.ok) throw new Error(`results HTTP ${response.status}`);
        const payload = await response.json();
        const items = payload.items || [];
        document.getElementById("total-count").textContent = `（共 ${payload.total || 0} 条）`;
        document.getElementById("records").innerHTML = items.length ? `<div class="record-grid">${items.map((item) => `
          <article class="result-card">
            <div class="record-head"><strong>${text(item.lesson_title, "未命名课堂")}</strong>${sampleBadge(item)}${statusBadge(item.status)}</div>
            <p class="muted">${text(item.classroom_name)} · ${text(item.classroom_id)}<br>${text(item.generated_at || item.recorded_at)}</p>
            <div class="score-row">
              ${metricCards(item)}
            </div>
            <p class="muted">视频证据：${item.has_video ? "可用" : "待接入"} · ${text(item.video_status)}</p>
            <div class="action-row"><a class="button secondary" href="${item.detail_url}">课堂分析</a><a class="button secondary" href="/teacher/reports?result_id=${item.result_id}">查看报告</a></div>
          </article>`).join("")}</div>` : `<div class="empty">当前筛选条件下没有课堂记录。</div>`;
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const params = new URLSearchParams(new FormData(event.target)); [...params.keys()].forEach((key) => { if (!params.get(key)) params.delete(key); }); window.location.search = params.toString(); });
      (async function init() { try { applyParamsToForm(); await loadClassrooms(); applyParamsToForm(); await loadRecords(); } catch (error) { document.getElementById("page-error").textContent = `课堂记录加载失败：${error}`; } })();
    </script>
    """
    return _shell("课堂记录中心", "results", "teacher-results-page", body, current_user)


def build_teacher_trends_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">教学趋势分析</p>
      <h1>趋势洞察</h1>
      <p class="muted">默认只展示真实课堂数据；选择演示数据或全部数据时，页面会明确提示，避免展示口径混淆。</p>
    </section>
    <section class="card">
      <form id="filters" class="filters">
        <div><label>班级</label><input name="classroom_id" id="classroom_id" placeholder="classroom_101" /></div>
        <div><label>开始日期</label><input name="date_from" id="date_from" type="date" /></div>
        <div><label>结束日期</label><input name="date_to" id="date_to" type="date" /></div>
        <div><label>数据来源</label><select name="data_source" id="data_source"><option value="real">真实数据</option><option value="demo">演示数据</option><option value="all">全部数据</option></select></div>
        <div><label>数量</label><input name="limit" id="limit" type="number" min="1" max="100" value="20" /></div>
        <button class="button" type="submit">筛选</button>
      </form>
      <div class="action-row" data-marker="phase319-trends-retired-entry"><a class="button secondary" href="/teacher/reports">打开报告中心</a></div>
      <div id="source-warning"></div>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="phase30-teacher-trends-overview"></section>
    <section class="chart-side-grid">
      <div class="chart-panel dashboard-main"><h2>教学反馈趋势主图</h2><p class="muted">用多节课反馈曲线识别教学质量变化、低谷片段和最近课堂表现。</p><div id="score-chart" class="chart chart-hero" data-marker="phase30-score-trend-chart"></div></div>
      <aside class="insight-panel dashboard-side"><h2>复盘优先级</h2><p class="muted">优先查看专注或互动波动较大的课堂。</p><div id="risk-lessons" class="list"></div></aside>
    </section>
    <section class="grid">
      <div class="chart-panel"><h2>专注度 / 活跃度趋势</h2><p class="muted">判断学生课堂参与状态是否稳定。</p><div id="attention-chart" class="chart" data-marker="phase30-attention-activity-chart"></div></div>
      <div class="chart-panel"><h2>提问 / 响应趋势</h2><p class="muted">关注互动触发和学生回应质量。</p><div id="question-chart" class="chart" data-marker="phase30-question-response-chart"></div></div>
      <div class="chart-panel"><h2>教学阶段结构</h2><p class="muted">查看讲授、讨论、总结和课堂组织的比例。</p><div id="stage-chart" class="chart" data-marker="phase30-stage-chart"></div></div>
      <div class="card insight-card"><h2>规则教学建议</h2><div id="recommendations" class="list"></div></div>
    </section>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <script>
      const text = (v, f="暂无") => v === null || v === undefined || v === "" ? f : v;
      const params = () => new URLSearchParams(window.location.search);
      function applyForm(){ const p=params(); ["classroom_id","date_from","date_to","data_source","limit"].forEach(k=>{const el=document.getElementById(k); if(el&&p.has(k)) el.value=p.get(k);}); }
      function chart(id, option){ if(!window.echarts) return; const el=document.getElementById(id); const inst=echarts.init(el); inst.setOption(option); window.addEventListener("resize",()=>inst.resize()); }
      async function load(){
        applyForm();
        const p=params(); if(!p.has("data_source")) p.set("data_source","real"); if(!p.has("limit")) p.set("limit","20");
        const r=await fetch(`/api/teacher/trends?${p.toString()}`); if(!r.ok) throw new Error(`HTTP ${r.status}`);
        const payload=await r.json(); const o=payload.overview||{}; const s=payload.series||{}; const q=payload.data_quality||{};
        const qualityNote = ((q.notes || [])[0]) || "";
        document.getElementById("source-warning").innerHTML = qualityNote ? `<div class="record">${qualityNote}</div>` : (q.demo_warning ? `<div class="warning">当前包含演示数据，仅用于功能兼容验证，不代表真实教学结论。</div>` : (q.insufficient_real_data ? `<div class="empty">真实多课堂数据不足，趋势洞察已从前端移除。<div class="action-row"><a class="button secondary" href="/teacher/reports">打开报告中心</a></div></div>` : ""));
        const labels=[["lesson_count","课堂数"],["avg_score","平均反馈"],["avg_attention_score","平均专注"],["avg_activity_score","平均活跃"],["risk_lesson_count","风险课堂"],["high_risk_count","高风险"]];
        document.getElementById("overview").innerHTML=labels.filter(([k])=>o[k]!==null&&o[k]!==undefined).map(([k,l])=>`<div class="metric"><span>${l}</span><strong>${text(o[k],0)}</strong></div>`).join("");
        const x=s.labels||[];
        chart("score-chart",{color:["#2563eb"],animationDuration:700,animationEasing:"cubicOut",tooltip:{trigger:"axis",formatter:(ps)=>ps.map(p=>`${p.axisValue}<br/>${p.marker}${p.seriesName}：${p.value}`).join("")},grid:{left:48,right:26,top:52,bottom:42},xAxis:{type:"category",data:x,axisLabel:{hideOverlap:true}},yAxis:{type:"value",min:0,max:100},series:[{type:"line",smooth:true,symbolSize:7,areaStyle:{opacity:.18},data:s.score||[],name:"教学反馈",markLine:{symbol:"none",lineStyle:{color:"#ea580c",type:"dashed"},data:[{yAxis:70,name:"重点复盘阈值"}]},markPoint:{symbolSize:46,data:[{type:"min",name:"低谷"}]}}]});
        chart("attention-chart",{color:["#2563eb","#0fba8c"],animationDuration:650,tooltip:{trigger:"axis"},legend:{data:["专注度","活跃度"]},grid:{left:42,right:20,top:48,bottom:42},xAxis:{type:"category",data:x,axisLabel:{hideOverlap:true}},yAxis:{type:"value",min:0,max:100},series:[{type:"line",smooth:true,areaStyle:{opacity:.1},data:s.attention_score||[],name:"专注度"},{type:"line",smooth:true,areaStyle:{opacity:.08},data:s.activity_score||[],name:"活跃度"}]});
        chart("question-chart",{color:["#f59e0b","#0891b2"],animationDuration:650,tooltip:{trigger:"axis"},legend:{data:["提问数","响应率"]},grid:{left:42,right:20,top:48,bottom:42},xAxis:{type:"category",data:x,axisLabel:{hideOverlap:true}},yAxis:{type:"value"},series:[{type:"bar",barMaxWidth:28,itemStyle:{borderRadius:[8,8,0,0]},data:s.question_count||[],name:"提问数"},{type:"line",smooth:true,data:s.response_rate||[],name:"响应率"}]});
        const stage=payload.stage_distribution||{}; chart("stage-chart",{color:["#4f83ff","#14b8a6","#f59e0b","#94a3b8","#fb7185"],tooltip:{trigger:"item"},legend:{bottom:0,type:"scroll"},series:[{type:"pie",radius:["48%","72%"],label:{formatter:"{b}\\n{d}%"},data:Object.entries(stage).map(([name,value])=>({name,value}))}]});
        const riskLabel=(v)=>({high:"高风险",medium:"中风险",low:"低风险",unknown:"未知"}[v]||v||"未知");
        const risks=payload.risk_lessons||[]; document.getElementById("risk-lessons").innerHTML=risks.length?risks.map(i=>`<div class="record"><strong>${text(i.lesson_title)}</strong><p class="muted">${text(i.classroom_name)} · ${text(i.created_at)} · ${riskLabel(i.risk_level)}</p><div class="action-row"><a class="button secondary" href="${i.report_url}">查看报告</a><a class="button secondary" href="${i.dashboard_url||'/dashboard?result_id='+i.result_id}">课堂分析</a></div></div>`).join(""):`<div class="empty">当前筛选范围没有明显重点复盘课堂。</div>`;
        const recs=payload.recommendations||[]; document.getElementById("recommendations").innerHTML=recs.map(i=>`<div class="record">${i}</div>`).join("")||`<div class="empty">暂无建议，建议继续积累课堂数据。</div>`;
      }
      document.getElementById("filters").addEventListener("submit",e=>{e.preventDefault();const p=new URLSearchParams(new FormData(e.target));[...p.keys()].forEach(k=>{if(!p.get(k))p.delete(k)});window.location.search=p.toString();});
      load().catch(e=>document.getElementById("page-error").textContent=`趋势洞察加载失败：${e}`);
    </script>
    """
    return _shell("趋势洞察", "trends", "phase30-teacher-trends-page", body, current_user)


def build_teacher_reports_html(current_user: Optional[dict] = None, result_id: Optional[str] = None) -> str:
    marker = "phase30-teacher-report-detail-page" if result_id else "phase30-teacher-reports-page"
    body = """
    <section class="hero">
      <p class="kicker">教学报告</p>
      <h1 id="title">报告中心</h1>
      <p class="muted">报告以课堂结论、风险原因、改进建议和数据依据组织；AI 综合评语未配置时，规则报告仍可完整展示。</p>
    </section>
    <p id="page-error" class="error"></p>
    <div id="app"></div>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <script>
      const initialResultId = "__RESULT_ID__";
      const text=(v,f="暂无")=>v===null||v===undefined||v===""?f:v;
      const riskLabel=(v)=>({low:"低风险",medium:"中风险",high:"高风险",sample:"展示样本",unknown:"未知"}[v]||v||"未知");
      const sourceLabel=(v)=>({real:"真实数据",demo:"演示数据",all:"全部数据",unknown:"未知"}[v]||v||"未知");
      const qualityParagraph=(v)=>v?'<p class="muted">'+text(v,'')+'</p>':'';
      const sampleBadge=(item)=>item&&item.display_badge?`<span class="badge sample">${text(item.display_badge)}</span>`:"";
      const metricText=(item)=>{const metrics=(item&&item.display_metrics)||[];return metrics.length?metrics.map((m)=>`${text(m.label)} ${text(m.value)}${m.suffix||""}`).join(" · "):text(item&&item.data_quality_note,"暂无可信指标");};
      const metricGrid=(metrics)=>{metrics=metrics||[];return metrics.length?`<section class="grid">${metrics.map((m)=>`<div class="metric"><span>${text(m.label)}</span><strong>${text(m.value)}${m.suffix||""}</strong></div>`).join("")}</section>`:`<section class="card"><div class="empty">当前记录暂无可用于展示的可信指标。</div></section>`;};
      const reportChartSection=(report,tl,st)=>{const profile=((report.presentation_scope||{}).metric_profile)||"standard";if(profile!=="standard")return `<section class="card"><h2>数据依据</h2><p class="muted">当前报告以视频证据、ASR 提问候选和视觉响应对齐为主，专注度与教学阶段分布不作为可信展示指标。</p></section>`;return `<section class="grid"><div class="chart-panel"><h2>数据依据：专注 / 活跃曲线</h2><div id="curve" class="chart"></div></div><div class="chart-panel"><h2>教学阶段结构</h2><div id="stage" class="chart"></div></div></section>`;};
      const params=()=>new URLSearchParams(window.location.search);
      function chart(id,opt){ if(window.echarts) echarts.init(document.getElementById(id)).setOption(opt); }
      function issueTitle(issue){ return issue.label || issue.tag || issue.issue_label || issue.type || issue.category || "增强问题"; }
      function enhancedIssuesSection(issues){
        if(!issues || !issues.length) return "";
        return `<section class="card" data-marker="phase32-report-enhanced-issues"><h2>规则分析建议（Enhanced Issues）</h2><p class="muted">以下内容来自本地端 Phase 3.2 enhanced JSON，不依赖 AI 生成。</p><div class="list">${issues.map((issue)=>`<div class="record"><div class="record-head"><strong>${issueTitle(issue)}</strong><span class="badge ${text(issue.severity,"unknown")}">${text(issue.severity,"unknown")}</span></div><p><strong>原因：</strong>${text(issue.reason)}</p><p><strong>证据：</strong>${text(issue.evidence)}</p><p><strong>建议：</strong>${text(issue.suggestion)}</p></div>`).join("")}</div></section>`;
      }
      function questionKindLabel(v){ return ({open:"开放提问",closed:"封闭提问",check:"检查理解",guiding:"引导追问",reasoning:"推理追问"}[v]||v||"未知类型"); }
      function questionGuidanceSection(summary, events, report){
        summary = summary || {}; events = Array.isArray(events) ? events : [];
        if(!events.length && !Object.keys(summary).length) return "";
        const dist = summary.question_distribution || summary.open_closed_check_distribution || summary.distribution || {};
        const coverage = summary.stage_coverage || summary.coverage || summary.early_middle_late_coverage || {};
        const rawExamples = summary.top_examples || summary.examples || [];
        const examples = (Array.isArray(rawExamples) && rawExamples.length ? rawExamples : events).slice(0,4);
        const isDemo = [summary.source, summary.status, report.dataset_source].some(v=>v==="demo"||v==="demo_seed");
        const distHtml = Object.entries(dist).map(([k,v])=>`<span class="badge">${questionKindLabel(k)} ${text(v)}</span>`).join(" ") || `<span class="muted">暂无提问类型分布。</span>`;
        const coverageHtml = Object.entries(coverage).map(([k,v])=>`<span class="badge">${({early:"前段",middle:"中段",late:"后段"}[k]||k)} ${text(v)}</span>`).join(" ") || `<span class="muted">暂无课堂阶段覆盖。</span>`;
        const exampleHtml = examples.length ? examples.map((event)=>`<div class="record"><strong>${text(event.text||event.question_text||event.prompt||event.label,"未标注提问")}</strong><p class="muted">${questionKindLabel(event.question_type||event.type||event.category)} · ${text(event.start_sec||event.time_sec||event.timestamp_sec,"未知")}s</p><p><strong>响应：</strong>${text(event.response_signal||event.response||event.student_response)}</p><p><strong>建议：</strong>${text(event.guidance||event.suggestion)}</p></div>`).join("") : `<div class="empty">未提供独立提问引导示例；如样本包含 ASR 提问候选，请以课堂分析详情页为准。</div>`;
        return `<section class="card" data-marker="phase33-report-question-guidance"><div class="record-head"><h2>教学提问引导分析</h2>${isDemo?`<span class="badge sample">演示数据</span>`:""}</div><section class="grid"><div class="metric"><span>提问数量</span><strong>${text(summary.question_count||summary.teacher_question_count||events.length,0)}</strong></div><div class="metric"><span>引导评分</span><strong>${text(summary.guidance_score||summary.score)}</strong></div><div class="metric"><span>响应信号</span><strong>${text(summary.response_signal_summary||summary.response_signal)}</strong></div></section><div class="record"><strong>提问分布</strong><p>${distHtml}</p><strong>阶段覆盖</strong><p>${coverageHtml}</p></div><div class="grid"><div class="record"><h3>主要问题</h3><p>${text(summary.main_issue||summary.issue)}</p><p><strong>证据：</strong>${text(summary.evidence)}</p></div><div class="record"><h3>改进建议</h3><p>${text(summary.suggestion)}</p></div></div><h3>提问时间线与示例</h3><div class="list">${exampleHtml}</div></section>`;
      }
      async function loadList(){
        const p=params(); if(!p.has("data_source")) p.set("data_source","real"); if(!p.has("limit")) p.set("limit","20");
        const r=await fetch(`/api/teacher/reports?${p.toString()}`); if(!r.ok) throw new Error(`HTTP ${r.status}`);
        const payload=await r.json(); const items=payload.items||[];
        const highRisk=items.filter(i=>i.risk_level==="high").length;
        const pending=items.filter(i=>i.status==="raw" || i.risk_level==="medium" || i.risk_level==="high").length;
        document.getElementById("app").innerHTML=`<section class="grid"><div class="metric"><span>报告数</span><strong>${items.length}</strong></div><div class="metric"><span>高风险</span><strong>${highRisk}</strong></div><div class="metric"><span>待复盘</span><strong>${pending}</strong></div><div class="metric"><span>AI 状态</span><strong>可选</strong></div></section><section class="card"><form id="filters" class="filters"><div><label>班级</label><input name="classroom_id" value="${text(p.get("classroom_id"),"")}"></div><div><label>开始日期</label><input type="date" name="date_from" value="${text(p.get("date_from"),"")}"></div><div><label>结束日期</label><input type="date" name="date_to" value="${text(p.get("date_to"),"")}"></div><div><label>数据来源</label><select name="data_source"><option value="real">真实数据</option><option value="demo">演示数据</option><option value="all">全部数据</option></select></div><div><label>数量</label><input name="limit" type="number" min="1" max="100" value="${text(p.get("limit"),"20")}"></div><button class="button">筛选</button></form>${(payload.filters||{}).data_source!=="real"?`<div class="warning">当前包含演示数据，请勿与真实教学趋势混淆。</div>`:""}</section><section class="grid" id="reports"></section>`;
        document.querySelector("[name=data_source]").value=(payload.filters||{}).data_source||"real";
        document.getElementById("filters").addEventListener("submit",e=>{e.preventDefault();const q=new URLSearchParams(new FormData(e.target));[...q.keys()].forEach(k=>{if(!q.get(k))q.delete(k)});window.location.search=q.toString();});
        document.getElementById("reports").innerHTML=items.length?items.map(i=>`<article class="report-card"><div class="record-head"><h2>${text(i.lesson_title,"未命名课堂")}</h2>${sampleBadge(i)}<span class="badge ${text(i.risk_level,"unknown")}">${riskLabel(i.risk_level)}</span></div><p class="muted">${text(i.classroom_name)} · ${text(i.created_at)} · ${sourceLabel(i.dataset_source)}</p>${qualityParagraph(i.data_quality_note)}<p>${metricText(i)}</p><p class="muted">核心结论：按当前样本口径展示可信数据，历史阶段和旧测试记录已从默认列表隔离。</p><p class="muted">建议摘要：优先结合课堂分析页查看视频证据、ASR 提问候选和响应对齐。</p><div class="action-row"><a class="button" href="${i.report_url}">查看报告</a> <a class="button secondary" href="${i.dashboard_url}">打开课堂分析</a></div></article>`).join(""):`<div class="empty">当前没有可展示的课堂报告。</div>`;
      }
      async function loadDetail(id){
        const r=await fetch(`/api/teacher/reports/detail?result_id=${encodeURIComponent(id)}`); if(!r.ok) throw new Error(`HTTP ${r.status}`);
        const payload=await r.json(); const report=payload.report||{}; const b=report.basic||{}, sc=report.scores||{}, qa=report.question_analysis||{}, st=report.stage_distribution||{}, tl=report.timeline||{};
        const enhancedIssues = report.enhanced_issues || ((report.phase32||{}).enhanced_issues) || [];
        const questionGuidanceSummary = report.question_guidance_summary || ((report.phase33||{}).question_guidance_summary) || {};
        const teacherQuestionEvents = report.teacher_question_events || ((report.phase33||{}).teacher_question_events) || [];
        document.getElementById("title").textContent=`课堂报告：${text(b.lesson_title)}`;
        document.getElementById("app").innerHTML=`${metricGrid(report.display_metrics || [])}<section class="card"><h2>课堂基本信息 ${sampleBadge(report)}</h2><p>${text(b.classroom_name)} · ${text(b.teacher_name)} · ${text(b.created_at)} · ${sourceLabel(report.dataset_source)}</p>${qualityParagraph(report.data_quality_note)}<a class="button secondary" href="${report.dashboard_url}">打开原始课堂分析</a></section>${reportChartSection(report,tl,st)}<section class="grid"><div class="card"><h2>课堂结论</h2>${(report.highlights||[]).map(x=>`<div class="record">${x}</div>`).join("")}<h2>主要风险</h2>${(report.risks||[]).map(x=>`<div class="record">${x}</div>`).join("")||"<div class='empty'>暂无明显风险。</div>"}</div><div class="insight-panel"><h2>改进建议</h2>${(report.recommendations||[]).map(x=>`<div class="record">${x}</div>`).join("")}</div></section>${(((report.presentation_scope||{}).metric_profile)||"standard")==="standard"?enhancedIssuesSection(enhancedIssues):""}${questionGuidanceSection(questionGuidanceSummary, teacherQuestionEvents, report)}<section class="card"><h2>提问与响应分析</h2><p>提问数：${text(qa.question_count,0)} · 响应率：${text(qa.response_rate,0)}</p><div class="list">${(qa.events||[]).map(e=>`<div class="record">${text(e.text)}<br><span class="muted">${text(e.start_sec)}s</span></div>`).join("")||"<div class='empty'>暂无提问事件。</div>"}</div></section><section class="card"><h2>AI 综合评语</h2><p id="ai-status" class="muted">AI 综合评语未启用时，当前展示规则报告。</p><div id="ai-content" class="record">${text((report.ai_summary||{}).content,"未配置或尚未生成。")}</div><button class="button" id="ai-button">生成 AI 综合评语</button></section>`;
        if(((report.presentation_scope||{}).metric_profile||"standard")==="standard"){
          chart("curve",{color:["#2563eb","#10b981"],tooltip:{trigger:"axis"},legend:{data:["专注度","活跃度"]},xAxis:{type:"category",data:(tl.attention_curve||[]).map((_,i)=>i+1)},yAxis:{type:"value"},series:[{type:"line",smooth:true,data:tl.attention_curve||[],name:"专注度"},{type:"line",smooth:true,data:tl.activity_curve||[],name:"活跃度"}]});
          chart("stage",{color:["#2563eb"],tooltip:{},xAxis:{type:"category",data:Object.keys(st)},yAxis:{type:"value"},series:[{type:"bar",data:Object.values(st)}]});
        }
        document.getElementById("ai-button").onclick=async()=>{const rr=await fetch("/api/teacher/reports/ai-summary",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({result_id:id})}); const p=await rr.json(); const ai=p.ai_summary||{}; document.getElementById("ai-status").textContent=ai.status||"未知"; document.getElementById("ai-content").textContent=ai.content||ai.error||"AI 综合评语暂不可用，规则报告不受影响。";};
      }
      (initialResultId ? loadDetail(initialResultId) : loadList()).catch(e=>document.getElementById("page-error").textContent=`报告中心加载失败：${e}`);
    </script>
    """.replace("__RESULT_ID__", result_id or "")
    return _shell("报告中心", "reports", marker, body, current_user)
