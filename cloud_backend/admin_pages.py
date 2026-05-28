"""Admin console pages for V2 Phase 2.7."""
from __future__ import annotations

from typing import Optional

from .ui_style import PHASE31_STYLE, role_label


ADMIN_STYLE = PHASE31_STYLE


def _identity_bar(current_user: Optional[dict]) -> str:
    if not current_user:
        return ""
    display_name = current_user.get("display_name") or current_user.get("username") or "用户"
    role = role_label(current_user.get("role") or "")
    return f"""
      <div class="identity" data-marker="phase29-user-identity">
        <span>{display_name} · {role}</span>
        <button class="logout" type="button" onclick="fetch('/api/auth/logout', {{method: 'POST'}}).finally(() => window.location.href='/login')">退出</button>
      </div>
    """


def _admin_nav(active: str, current_user: Optional[dict] = None) -> str:
    active_class = {
        "overview": "active" if active == "overview" else "",
        "classrooms": "active" if active == "classrooms" else "",
        "teachers": "active" if active == "teachers" else "",
        "results": "active" if active == "results" else "",
        "ingestion": "active" if active == "ingestion" else "",
    }
    return f"""
    <nav class="nav" data-marker="admin-console-nav">
      <div>
        <strong>智能课堂行为分析与教学反馈平台</strong>
        <span class="badge">管理员端</span>
      </div>
      <div class="nav-links">
        <a class="{active_class['overview']}" href="/admin">平台总览</a>
        <a class="{active_class['classrooms']}" href="/admin/classrooms">班级管理</a>
        <a class="{active_class['teachers']}" href="/admin/teachers">教师管理</a>
        <a class="{active_class['results']}" href="/admin/results">课堂数据</a>
        <a class="{active_class['ingestion']}" href="/admin/ingestion">接入状态</a>
        <a href="/teacher">教师端预览</a>
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
  {ADMIN_STYLE}
</head>
<body>
  <div class="page" data-marker="{marker}">
    {_admin_nav(active, current_user)}
    <main class="page-main">
      {body}
    </main>
  </div>
</body>
</html>"""


def build_admin_home_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">平台控制台</p>
      <h1>平台总览</h1>
      <p class="muted">统一查看采集、本地分析、云端入库和教师反馈的全平台运行情况。</p>
      <div class="pipeline" data-marker="admin-data-pipeline"><span>采集端或外部样本</span><span>-></span><span>本地分析</span><span>-></span><span>云端入库</span><span>-></span><span>教师反馈</span></div>
    </section>
    <p id="page-error" class="error"></p>
    <section id="metric-grid" class="grid" data-marker="admin-overview-metrics"></section>
    <section class="two-col">
      <div class="card">
        <h2>最近课堂结果</h2>
        <div id="latest-results" class="list" data-marker="admin-latest-results"></div>
      </div>
      <div class="card">
        <h2>数据接入状态</h2>
        <div id="system-status" data-marker="admin-system-status"></div>
        <h2>状态分布</h2>
        <div id="status-distribution" class="status-row" data-marker="admin-status-distribution"></div>
      </div>
    </section>
    <section class="card">
      <h2>快捷入口</h2>
      <div id="quick-links" class="grid" data-marker="admin-quick-links"></div>
    </section>
    <script>
      const metricLabels = {
        teacher_count: "教师数",
        classroom_count: "班级数",
        result_count: "课堂结果",
        recent_result_count: "近期结果",
        today_result_count: "今日上传",
        raw_count: "待处理",
        reviewed_count: "已复盘",
        archived_count: "已归档",
        avg_feedback_score: "平均反馈",
        avg_attention_score: "平均专注",
        avg_response_score: "平均响应"
      };
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function statusLabel(status) { return {raw:"待复盘", reviewed:"已复盘", archived:"已归档"}[status] || status || "待复盘"; }
      function statusBadge(status) { const safeStatus = status || "raw"; return `<span class="badge ${safeStatus}">${statusLabel(safeStatus)}</span>`; }
      function qualityLine(value) { return value ? '<br><span class="muted">' + text(value, '') + '</span>' : ''; }
      function sampleBadge(item) { return item && item.display_badge ? `<span class="badge sample">${text(item.display_badge)}</span>` : ''; }
      function metricLine(item) { const metrics = (item && item.display_metrics) || []; return metrics.length ? metrics.map((m) => `${text(m.label)} ${text(m.value)}${m.suffix || ''}`).join(' / ') : text(item && item.data_quality_note, '暂无可信指标'); }
      function quickLabel(label) { return {"Classrooms":"班级管理","Teachers":"教师管理","Classroom Data":"课堂数据","Teacher Console":"教师端预览","Ingestion Status":"接入状态"}[label] || label; }
      async function loadAdminOverview() {
        try {
          const response = await fetch("/api/admin/overview");
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const metrics = payload.metrics || {};
          document.getElementById("metric-grid").innerHTML = Object.entries(metricLabels).filter(([key]) => metrics[key] !== null && metrics[key] !== undefined).map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(metrics[key], 0)}</strong></div>`).join("");
          const status = payload.system_status || {};
          document.getElementById("system-status").innerHTML = `<div class="record"><p><strong>云端服务：</strong> ${text(status.cloud_service)}</p><p><strong>数据库：</strong> ${text(status.database)}</p><p><strong>最近上传：</strong> ${text(status.latest_upload_at)}</p><p><strong>最近分析：</strong> ${text(status.latest_analysis_id)}</p><p class="muted">${text(status.latest_raw_path, "")}</p></div>`;
          const distribution = payload.status_distribution || {};
          document.getElementById("status-distribution").innerHTML = ["raw", "reviewed", "archived"].map((name) => `<a class="metric" href="/admin/results?status=${name}"><span>${statusLabel(name)}</span><strong>${distribution[name] || 0}</strong></a>`).join("");
          const latest = payload.latest_results || [];
          document.getElementById("latest-results").innerHTML = latest.length ? latest.map((item) => `<div class="record"><div class="record-head"><strong>${text(item.lesson_title)}</strong>${sampleBadge(item)}${statusBadge(item.status)}</div><p class="muted">${text(item.classroom_name)} / ${text(item.teacher_name)} / ${text(item.created_at || item.generated_at)}</p><p>${metricLine(item)}</p><a class="button secondary" href="${item.detail_url}">查看课堂分析</a></div>`).join("") : `<div class="empty">暂无课堂分析结果。</div>`;
          const links = payload.quick_links || [];
          document.getElementById("quick-links").innerHTML = links.map((item) => `<a class="record" href="${item.url}" style="text-decoration:none;color:inherit"><strong>${quickLabel(text(item.label))}</strong><p class="muted">${text(item.description)}</p></a>`).join("");
        } catch (error) {
          document.getElementById("page-error").textContent = `平台总览加载失败：${error}`;
        }
      }
      loadAdminOverview();
    </script>
    """
    return _shell("平台总览", "overview", "admin-overview-page", body, current_user)


def build_admin_classrooms_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">班级概览</p>
      <h1>班级与最近活跃情况</h1>
      <p class="muted">查看班级覆盖、教师映射、课堂结果数量、平均反馈质量和最近活跃班级。</p>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-classrooms-overview"></section>
    <section class="card">
      <form id="filters" class="filters" data-marker="admin-classrooms-filters">
        <div><label for="q">搜索</label><input id="q" name="q" placeholder="班级或教师" /></div>
        <div><label for="teacher_id">教师 ID</label><input id="teacher_id" name="teacher_id" placeholder="demo 或数字 ID" /></div>
        <button class="button" type="submit">筛选</button>
      </form>
    </section>
    <section class="two-col">
      <div class="card"><h2>班级列表</h2><div id="classroom-list" data-marker="admin-classroom-list"></div></div>
      <div class="card"><h2>最近活跃 / 表现排行</h2><div id="ranking" class="list" data-marker="admin-classroom-ranking"></div></div>
    </section>
    <script>
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function params() { return new URLSearchParams(window.location.search); }
      function applyForm() { const p = params(); ["q", "teacher_id"].forEach((key) => { const el = document.getElementById(key); if (el && p.has(key)) el.value = p.get(key); }); }
      async function loadClassrooms() {
        try {
          applyForm();
          const response = await fetch(`/api/admin/classrooms?${params().toString()}`);
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const overview = payload.overview || {};
          document.getElementById("overview").innerHTML = [["classroom_count", "班级数"], ["active_classroom_count", "活跃班级"], ["avg_feedback_score", "平均反馈"], ["latest_result_at", "最近结果"]].map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
          const items = payload.items || [];
          document.getElementById("classroom-list").innerHTML = items.length ? `<div class="table-scroll"><table><thead><tr><th>班级</th><th>教师</th><th>结果数</th><th>指标</th><th>状态</th><th>操作</th></tr></thead><tbody>${items.map((item) => `<tr><td>${text(item.classroom_name)}<br><span class="muted">${text(item.classroom_id)}</span></td><td>${text(item.teacher_name)}<br><span class="muted">${text(item.teacher_id)}</span></td><td>${item.result_count || 0}<br><span class="muted">${text(item.latest_result_at)}</span></td><td>反馈 ${text(item.avg_feedback_score, "N/A")} / 专注 ${text(item.avg_attention_score, "N/A")} / 响应 ${text(item.avg_response_score, "N/A")}</td><td>待处理 ${item.raw_count || 0}<br>已复盘 ${item.reviewed_count || 0}<br>已归档 ${item.archived_count || 0}</td><td><a class="button secondary" href="${item.results_url}">查看课堂</a></td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">当前筛选条件下没有匹配班级。</div>`;
          document.getElementById("ranking").innerHTML = items.slice().sort((a, b) => (b.result_count || 0) - (a.result_count || 0)).slice(0, 6).map((item) => `<div class="record"><strong>${text(item.classroom_name)}</strong><p class="muted">${item.result_count || 0} 条结果，平均反馈 ${text(item.avg_feedback_score, "N/A")}</p><a class="button secondary" href="${item.results_url}">打开</a></div>`).join("") || `<div class="empty">暂无排行数据。</div>`;
        } catch (error) {
          document.getElementById("page-error").textContent = `班级概览加载失败：${error}`;
        }
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      loadClassrooms();
    </script>
    """
    return _shell("班级管理", "classrooms", "admin-classrooms-page", body, current_user)


def build_admin_teachers_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">教师概览</p>
      <h1>教师覆盖与反馈质量</h1>
      <p class="muted">查看教师负责班级数、课堂结果活跃度、平均指标和教学反馈排行。</p>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-teachers-overview"></section>
    <section class="card"><form id="filters" class="filters" data-marker="admin-teachers-filters"><div><label for="q">搜索</label><input id="q" name="q" placeholder="教师或用户名" /></div><button class="button" type="submit">筛选</button></form></section>
    <section class="two-col">
      <div class="card"><h2>教师列表</h2><div id="teacher-list" data-marker="admin-teacher-list"></div></div>
      <div class="card"><h2>教师排行</h2><h3>负责班级数</h3><div id="classroom-ranking" class="list" data-marker="admin-teacher-classroom-ranking"></div><h3>平均反馈</h3><div id="feedback-ranking" class="list" data-marker="admin-teacher-feedback-ranking"></div></div>
    </section>
    <script>
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function params() { return new URLSearchParams(window.location.search); }
      function applyForm() { const p = params(); const q = document.getElementById("q"); if (q && p.has("q")) q.value = p.get("q"); }
      function teacherCard(item) { return `<div class="record"><strong>${text(item.teacher_name)}</strong><p class="muted">${text(item.username)} / ${text(item.teacher_id)}</p><p>${item.classroom_count || 0} 个班级，${item.result_count || 0} 条结果</p><p>平均反馈 ${text(item.avg_feedback_score, "N/A")}</p><a class="button secondary" href="${item.results_url}">查看课堂</a></div>`; }
      async function loadTeachers() {
        try {
          applyForm();
          const response = await fetch(`/api/admin/teachers?${params().toString()}`);
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const overview = payload.overview || {};
          document.getElementById("overview").innerHTML = [["teacher_count", "教师数"], ["teachers_with_classrooms", "已绑定班级"], ["teachers_with_results", "已有结果"], ["avg_feedback_score", "平均反馈"]].map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
          const items = payload.items || [];
          document.getElementById("teacher-list").innerHTML = items.length ? `<div class="table-scroll"><table><thead><tr><th>教师</th><th>覆盖范围</th><th>指标</th><th>最近结果</th><th>操作</th></tr></thead><tbody>${items.map((item) => `<tr><td>${text(item.teacher_name)}<br><span class="muted">${text(item.username)} / ${text(item.teacher_id)}</span></td><td>${item.classroom_count || 0} 个班级<br>${item.result_count || 0} 条结果</td><td>反馈 ${text(item.avg_feedback_score, "N/A")} / 专注 ${text(item.avg_attention_score, "N/A")} / 响应 ${text(item.avg_response_score, "N/A")}</td><td>${text(item.latest_result_at)}</td><td><a class="button secondary" href="${item.results_url}">查看课堂</a></td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">当前筛选条件下没有匹配教师。</div>`;
          document.getElementById("classroom-ranking").innerHTML = items.slice().sort((a, b) => (b.classroom_count || 0) - (a.classroom_count || 0)).slice(0, 5).map(teacherCard).join("") || `<div class="empty">暂无班级排行数据。</div>`;
          document.getElementById("feedback-ranking").innerHTML = items.slice().sort((a, b) => (b.avg_feedback_score || 0) - (a.avg_feedback_score || 0)).slice(0, 5).map(teacherCard).join("") || `<div class="empty">暂无反馈排行数据。</div>`;
        } catch (error) {
          document.getElementById("page-error").textContent = `教师概览加载失败：${error}`;
        }
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      loadTeachers();
    </script>
    """
    return _shell("教师管理", "teachers", "admin-teachers-page", body, current_user)


def build_admin_results_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">课堂数据</p>
      <h1>全平台课堂分析结果</h1>
      <p class="muted">按班级、教师、状态和时间范围筛选课堂分析结果，并直接进入单堂课堂分析。</p>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-results-overview"></section>
    <section class="card">
      <form id="filters" class="filters" data-marker="admin-results-filters">
        <div><label for="classroom_id">班级</label><select id="classroom_id" name="classroom_id"><option value="">全部班级</option></select></div>
        <div><label for="teacher_id">教师</label><select id="teacher_id" name="teacher_id"><option value="">全部教师</option></select></div>
        <div><label for="status">状态</label><select id="status" name="status"><option value="">全部状态</option><option value="raw">待处理</option><option value="reviewed">已复盘</option><option value="archived">已归档</option></select></div>
        <div><label for="days">时间范围</label><select id="days" name="days"><option value="7">最近 7 天</option><option value="30">最近 30 天</option><option value="all">全部</option></select></div>
        <div><label for="limit">数量</label><input id="limit" name="limit" type="number" min="1" max="100" value="20" /></div>
        <button class="button" type="submit">筛选</button>
      </form>
    </section>
    <section class="two-col">
      <div class="card"><h2>全部课堂结果</h2><div id="results-list" data-marker="admin-result-list"></div></div>
      <div class="card"><h2>状态分布与提示</h2><div id="status-distribution" class="status-row" data-marker="admin-results-status-distribution"></div><div id="tips" class="list" data-marker="admin-results-tips"></div></div>
    </section>
    <script>
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function statusLabel(status) { return {raw:"待复盘", reviewed:"已复盘", archived:"已归档"}[status] || status || "待复盘"; }
      function statusBadge(status) { const safeStatus = status || "raw"; return `<span class="badge ${safeStatus}">${statusLabel(safeStatus)}</span>`; }
      function qualityLine(value) { return value ? '<br><span class="muted">' + text(value, '') + '</span>' : ''; }
      function sampleBadge(item) { return item && item.display_badge ? `<span class="badge sample">${text(item.display_badge)}</span>` : ''; }
      function metricLine(item) { const metrics = (item && item.display_metrics) || []; return metrics.length ? metrics.map((m) => `${text(m.label)} ${text(m.value)}${m.suffix || ''}`).join(' / ') : text(item && item.data_quality_note, '暂无可信指标'); }
      function params() { return new URLSearchParams(window.location.search); }
      function applyForm() { const p = params(); ["classroom_id", "teacher_id", "status", "days", "limit"].forEach((key) => { const el = document.getElementById(key); if (el && p.has(key)) el.value = p.get(key); }); }
      async function loadFilters() {
        const [classroomResponse, teacherResponse] = await Promise.all([fetch("/api/admin/classrooms?limit=100"), fetch("/api/admin/teachers?limit=100")]);
        if (!classroomResponse.ok) throw new Error(`classrooms HTTP ${classroomResponse.status}`);
        if (!teacherResponse.ok) throw new Error(`teachers HTTP ${teacherResponse.status}`);
        const classrooms = (await classroomResponse.json()).items || [];
        const teachers = (await teacherResponse.json()).items || [];
        const classroomSelect = document.getElementById("classroom_id");
        const teacherSelect = document.getElementById("teacher_id");
        classrooms.forEach((item) => { const option = document.createElement("option"); option.value = item.classroom_id || ""; option.textContent = item.classroom_name || item.classroom_id || "未知班级"; classroomSelect.appendChild(option); });
        teachers.forEach((item) => { const option = document.createElement("option"); option.value = item.teacher_id || ""; option.textContent = item.teacher_name || item.username || "未知教师"; teacherSelect.appendChild(option); });
      }
      async function loadResults() {
        const response = await fetch(`/api/admin/results?${params().toString()}`);
        if (!response.ok) throw new Error(`results HTTP ${response.status}`);
        const payload = await response.json();
        const overview = payload.overview || {};
        document.getElementById("overview").innerHTML = [["result_count", "结果总数"], ["page_count", "当前页结果"], ["avg_feedback_score", "平均反馈"], ["avg_attention_score", "平均专注"], ["low_attention_count", "低专注课堂"], ["high_score_count", "高分课堂"]].filter(([key]) => overview[key] !== null && overview[key] !== undefined).map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
        const distribution = overview.status_distribution || {};
        document.getElementById("status-distribution").innerHTML = ["raw", "reviewed", "archived"].map((name) => `<a class="metric" href="/admin/results?status=${name}"><span>${statusLabel(name)}</span><strong>${distribution[name] || 0}</strong></a>`).join("");
        const tips = overview.tips || [];
        document.getElementById("tips").innerHTML = tips.map((item) => `<div class="record"><strong>${text(item.title)}</strong><p class="muted">${text(item.description)}</p></div>`).join("");
        const items = payload.items || [];
          document.getElementById("results-list").innerHTML = items.length ? `<div class="table-scroll"><table><thead><tr><th>班级</th><th>教师</th><th>课堂</th><th>指标</th><th>状态</th><th>视频</th><th>操作</th></tr></thead><tbody>${items.map((item) => `<tr><td>${text(item.classroom_name)}<br><span class="muted">${text(item.classroom_id)}</span></td><td>${text(item.teacher_name)}<br><span class="muted">${text(item.teacher_id)}</span></td><td>${text(item.lesson_title)}<br><span class="muted">${text(item.created_at || item.generated_at)}</span>${qualityLine(item.data_quality_note)}</td><td>${metricLine(item)}</td><td>${statusBadge(item.status)}</td><td>${item.has_video ? "可用" : "待接入"}<br><span class="muted">${text(item.video_status)}</span></td><td><a class="button secondary" href="${item.detail_url}">查看分析</a></td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">当前筛选条件下没有匹配课堂结果。</div>`;
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      (async function init() { try { await loadFilters(); applyForm(); await loadResults(); } catch (error) { document.getElementById("page-error").textContent = `课堂数据加载失败：${error}`; } })();
    </script>
    """
    return _shell("课堂数据", "results", "admin-results-page", body, current_user)


def build_admin_ingestion_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">数据接入状态</p>
      <h1>三端数据接入状态</h1>
      <p class="muted">展示采集端或外部样本、本地分析、云端入库和教师反馈之间的链路状态。</p>
      <div id="pipeline" class="flow-board" data-marker="admin-ingestion-pipeline"></div>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-ingestion-overview"></section>
    <section class="card">
      <form id="filters" class="filters" data-marker="admin-ingestion-filters">
        <div><label for="classroom_id">班级</label><input id="classroom_id" name="classroom_id" placeholder="classroom_101" /></div>
        <div><label for="device_id">设备</label><input id="device_id" name="device_id" placeholder="pi-classroom-101" /></div>
        <div><label for="source_host">来源主机</label><input id="source_host" name="source_host" placeholder="local analyzer host" /></div>
        <div><label for="days">时间范围</label><select id="days" name="days"><option value="7">最近 7 天</option><option value="30">最近 30 天</option><option value="all">全部</option></select></div>
        <div><label for="limit">数量</label><input id="limit" name="limit" type="number" min="1" max="100" value="20" /></div>
        <button class="button" type="submit">筛选</button>
      </form>
    </section>
    <section class="dashboard-grid">
      <div class="card dashboard-main">
        <h2>设备 / 分析端状态</h2>
        <div id="device-list" data-marker="admin-ingestion-devices"></div>
      </div>
      <div class="insight-panel dashboard-side">
        <h2>视频可用性</h2>
        <div id="video-summary" class="status-row" data-marker="admin-ingestion-video-summary"></div>
        <h2>数据质量进度</h2>
        <div class="progress-track"><div id="metadata-progress" class="progress-fill" style="width:0%"></div></div>
        <h2>数据质量提示</h2>
        <div id="validation-hints" class="list" data-marker="admin-ingestion-validation-hints"></div>
      </div>
    </section>
    <section class="card">
      <h2>最近接入记录</h2>
      <div id="recent-ingestions" data-marker="admin-ingestion-recent"></div>
    </section>
    <script>
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function params() { return new URLSearchParams(window.location.search); }
      function statusPill(value) { const safe = value || "unknown"; const labels = {online:"在线", stale:"可能过期", offline:"离线", unknown:"未知", playable:"可播放", pending:"待接入", missing:"缺失", ok:"正常", warning:"提示", failed:"失败", ready:"就绪", inferred:"推断", partial:"部分完整", complete:"完整", success:"成功"}; return `<span class="status-pill ${safe}">${labels[safe] || safe}</span>`; }
      function stageLabel(value) { return {"Raspberry Pi Capture":"采集端或外部样本","Capture or External Sample":"采集端或外部样本","Local Analysis":"本地分析","Cloud Storage":"云端入库","Teacher Feedback":"教师反馈"}[value] || value; }
      function qualityParagraph(value) { return value ? '<p class="muted">' + text(value, '') + '</p>' : ''; }
      function applyForm() { const p = params(); ["classroom_id", "device_id", "source_host", "days", "limit"].forEach((key) => { const el = document.getElementById(key); if (el && p.has(key)) el.value = p.get(key); }); }
      async function loadIngestion() {
        try {
          applyForm();
          const response = await fetch(`/api/admin/ingestion?${params().toString()}`);
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const overview = payload.overview || {};
          const metricLabels = [
            ["total_results", "接入结果"],
            ["active_devices", "在线设备"],
            ["stale_devices", "过期设备"],
            ["offline_devices", "离线设备"],
            ["playable_videos", "可播放视频"],
            ["pending_videos", "待接入视频"],
            ["missing_videos", "缺失视频"],
            ["metadata_complete_rate", "元数据完整率"]
          ];
          document.getElementById("overview").innerHTML = metricLabels.map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
          const pipeline = payload.pipeline || [];
          document.getElementById("metadata-progress").style.width = `${Math.max(0, Math.min(100, Number(overview.metadata_complete_rate || 0)))}%`;
          document.getElementById("pipeline").innerHTML = pipeline.map((item) => `<div class="flow-step ${item.status || "unknown"}"><strong>${stageLabel(text(item.stage))}</strong><p>${statusPill(item.status)} · ${text(item.count, 0)} 条记录</p><p class="muted">${text(item.description)}</p></div>`).join("");
          const devices = payload.devices || [];
          document.getElementById("device-list").innerHTML = devices.length ? `<div class="table-scroll"><table><thead><tr><th>设备</th><th>班级</th><th>来源</th><th>最近上传</th><th>状态</th><th>视频</th></tr></thead><tbody>${devices.map((item) => `<tr><td>${text(item.device_name)}<br><span class="muted">${text(item.device_id)}</span></td><td>${text(item.classroom_id)}</td><td>${text(item.source_host)}</td><td>${text(item.latest_upload_time)}<br><span class="muted">${item.total_sessions || 0} 条记录</span></td><td>${statusPill(item.freshness)}<br><span class="muted">${statusPill(item.metadata_quality)}</span></td><td>${statusPill(item.video_status)}<br><span class="muted">标准化：${item.standardized_video_present ? "是" : "否"}</span><br><span class="muted">浏览器：${item.browser_compatible === true ? "兼容" : item.browser_compatible === false ? "不兼容" : "未知"}</span></td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">当前筛选条件下暂无设备或分析端状态。</div>`;
          const video = payload.video_summary || {};
          const videoLabels = {playable:"可播放", pending:"待接入", missing:"缺失", unknown:"未知", standardized_present:"已标准化", browser_compatible:"浏览器兼容", browser_incompatible:"浏览器不兼容", transcode_failed:"转码失败"};
          document.getElementById("video-summary").innerHTML = ["playable", "pending", "missing", "unknown", "standardized_present", "browser_compatible", "browser_incompatible", "transcode_failed"].map((name) => `<div class="metric"><span>${videoLabels[name] || name}</span><strong>${video[name] || 0}</strong></div>`).join("");
          const hints = payload.validation_hints || [];
          document.getElementById("validation-hints").innerHTML = hints.map((item) => `<div class="record"><div class="record-head"><strong>${text(item.type)}</strong>${statusPill(item.severity)}</div><p class="muted">${text(item.message)}</p></div>`).join("") || `<div class="empty">暂无数据质量提示。</div>`;
          const recent = payload.recent_ingestions || [];
          document.getElementById("recent-ingestions").innerHTML = recent.length ? `<div class="grid">${recent.map((item) => `<article class="report-card"><div class="record-head"><strong>${text(item.lesson_title)}</strong>${statusPill(item.video_status)}</div><p class="muted">${text(item.result_id)}</p><p>${text(item.classroom_id)} · ${text(item.device_id)} · ${text(item.source_host)}</p><p class="muted">来源：${text(item.capture_label || "采集端或外部样本")}<br>采集：${text(item.capture_time)}<br>上传：${text(item.upload_time)}</p>${qualityParagraph(item.data_quality_note)}<p>标准化：${item.standardized_video_present ? "是" : "否"} · 浏览器：${item.browser_compatible === true ? "兼容" : item.browser_compatible === false ? "不兼容" : "未知"} · 转码：${statusPill(item.transcode_status)}</p><div class="action-row"><a class="button secondary" href="${item.detail_url}">打开课堂分析</a></div></article>`).join("")}</div>` : `<div class="empty">当前筛选条件下暂无接入记录。</div>`;
        } catch (error) {
          document.getElementById("page-error").textContent = `接入状态加载失败：${error}`;
        }
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      loadIngestion();
    </script>
    """
    return _shell("接入状态", "ingestion", "admin-ingestion-page", body, current_user)


def build_admin_trends_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">平台趋势</p>
      <h1>平台趋势洞察</h1>
      <p class="muted">查看班级表现排行、教师活跃度、风险课堂和最近报告摘要。默认仅使用真实数据。</p>
    </section>
    <section class="card">
      <form id="filters" class="filters" data-marker="phase30-admin-trends-filters">
        <div><label>班级</label><input id="classroom_id" name="classroom_id" placeholder="classroom_101" /></div>
        <div><label>教师</label><input id="teacher_id" name="teacher_id" placeholder="teacher id" /></div>
        <div><label>开始日期</label><input id="date_from" name="date_from" type="date" /></div>
        <div><label>结束日期</label><input id="date_to" name="date_to" type="date" /></div>
        <div><label>数据来源</label><select id="data_source" name="data_source"><option value="real">真实数据</option><option value="demo">演示数据</option><option value="all">全部数据</option></select></div>
        <div><label>数量</label><input id="limit" name="limit" type="number" min="1" max="100" value="30" /></div>
        <button class="button" type="submit">筛选</button>
      </form>
      <div class="action-row" data-marker="phase319-admin-trends-retired-entry"><a class="button secondary" href="/admin/results">打开课堂数据</a></div>
      <div id="source-warning"></div>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="phase30-admin-trends-overview"></section>
    <section class="dashboard-grid">
      <div class="chart-panel dashboard-main"><h2>平台课堂质量趋势</h2><p class="muted">基于最近课堂报告的反馈分变化，观察平台教学质量和重点复盘区间。</p><div id="admin-trend-chart" class="chart chart-hero"></div></div>
      <div class="insight-panel dashboard-side"><h2>班级表现排行</h2><div id="classroom-rankings" data-marker="phase30-classroom-ranking"></div></div>
    </section>
    <section class="two-col">
      <div class="card"><h2>教师课堂数量排行</h2><div id="teacher-activity" data-marker="phase30-teacher-activity"></div></div>
      <div class="card"><h2>平台风险分布</h2><p class="muted">低分或高风险课堂会进入复盘优先级，帮助管理员快速定位班级和教师支持需求。</p><div class="heat-strip"><span class="strip-cell high"></span><span class="strip-cell medium"></span><span class="strip-cell low"></span><span class="strip-cell high question"></span><span class="strip-cell medium"></span><span class="strip-cell high"></span><span class="strip-cell low"></span><span class="strip-cell medium question"></span><span class="strip-cell high"></span><span class="strip-cell high"></span><span class="strip-cell medium"></span><span class="strip-cell high"></span></div></div>
    </section>
    <section class="two-col">
      <div class="card"><h2>低分 / 风险课堂</h2><div id="risk-lessons" data-marker="phase30-admin-risk-lessons"></div></div>
      <div class="card"><h2>最近报告摘要</h2><div id="recent-reports" data-marker="phase30-admin-recent-reports"></div></div>
    </section>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <script>
      const text=(v,f="N/A")=>v===null||v===undefined||v===""?f:v;
      const params=()=>new URLSearchParams(window.location.search);
      const riskLabel=(v)=>({high:"高风险",medium:"中风险",low:"低风险",unknown:"未知"}[v]||v||"未知");
      const sourceLabel=(v)=>({real:"真实数据",demo:"演示数据",all:"全部数据"}[v]||v||"未知");
      const qualityLine=(v)=>v?'<br><span class="muted">'+text(v,'')+'</span>':'';
      function applyForm(){const p=params();["classroom_id","teacher_id","date_from","date_to","data_source","limit"].forEach(k=>{const el=document.getElementById(k);if(el&&p.has(k))el.value=p.get(k);});}
      function table(items, cols){return items.length?`<div class="table-scroll"><table><thead><tr>${cols.map(c=>`<th>${c[1]}</th>`).join("")}</tr></thead><tbody>${items.map(i=>`<tr>${cols.map(c=>`<td>${c[0](i)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`:`<div class="empty">当前筛选条件下暂无数据。</div>`;}
      function rankCards(items, valueKey, label){
        if(!items.length)return `<div class="empty">当前筛选条件下暂无排行数据。</div>`;
        const max=Math.max(...items.map(i=>Number(i[valueKey]||0)),1);
        return `<div class="rank-bar">${items.slice(0,8).map((i)=>{const value=Number(i[valueKey]||0);const pct=Math.max(4,Math.round(value/max*100));return `<div class="record"><div class="record-head"><strong>${text(i.classroom_name||i.teacher_name)}</strong><span class="badge">${value} ${label}</span></div><p class="muted">${text(i.classroom_id||i.teacher_id)}</p><div class="rank-line"><span style="width:${pct}%"></span></div></div>`}).join("")}</div>`;
      }
      function drawTrend(reports){if(!window.echarts)return;const items=(reports||[]).slice().reverse();const chart=echarts.init(document.getElementById("admin-trend-chart"));chart.setOption({color:["#2563eb"],animationDuration:700,tooltip:{trigger:"axis"},grid:{left:48,right:24,top:48,bottom:42},xAxis:{type:"category",data:items.map(i=>text(i.lesson_title,"课堂")).map(v=>String(v).slice(0,8)),axisLabel:{hideOverlap:true}},yAxis:{type:"value",min:0,max:100},series:[{name:"反馈分",type:"line",smooth:true,symbolSize:7,areaStyle:{opacity:.16},data:items.map(i=>Number(i.score||0)),markLine:{symbol:"none",lineStyle:{color:"#ea580c",type:"dashed"},data:[{yAxis:70,name:"重点复盘阈值"}]}}]});window.addEventListener("resize",()=>chart.resize());}
      async function load(){applyForm();const p=params();if(!p.has("data_source"))p.set("data_source","real");if(!p.has("limit"))p.set("limit","30");const r=await fetch(`/api/admin/trends?${p.toString()}`);if(!r.ok)throw new Error(`HTTP ${r.status}`);const payload=await r.json();const o=payload.overview||{}, q=payload.data_quality||{};const qualityNote=((q.notes||[])[0])||"";document.getElementById("source-warning").innerHTML=qualityNote?`<div class="record">${qualityNote}</div>`:(q.demo_warning?`<div class="record" style="background:#fff7ed;color:#9a3412">当前包含演示或全部数据，仅用于兼容验证，不代表真实教学结论。</div>`:(q.insufficient_real_data?`<div class="empty">真实多课堂数据不足，趋势洞察已从前端移除。<div class="action-row"><a class="button secondary" href="/admin/results">打开课堂数据</a></div></div>`:""));const labels=[["lesson_count","课堂数"],["avg_score","平均反馈"],["avg_attention_score","平均专注"],["avg_activity_score","平均活跃"],["risk_lesson_count","风险课堂"],["high_risk_count","高风险"]];document.getElementById("overview").innerHTML=labels.filter(([k])=>o[k]!==null&&o[k]!==undefined).map(([k,l])=>`<div class="metric"><span>${l}</span><strong>${text(o[k],0)}</strong></div>`).join("");drawTrend(payload.recent_reports||[]);document.getElementById("classroom-rankings").innerHTML=rankCards(payload.classroom_rankings||[],"avg_score","平均反馈");document.getElementById("teacher-activity").innerHTML=rankCards(payload.teacher_activity||[],"lesson_count","节课");document.getElementById("risk-lessons").innerHTML=table(payload.risk_lessons||[],[[i=>`${text(i.lesson_title)}<br><span class="muted">${text(i.classroom_name)}</span>${qualityLine(i.data_quality_note)}`,"课堂"],[i=>text(i.score,0),"反馈分"],[i=>riskLabel(i.risk_level),"风险"],[i=>`<a class="button secondary" href="${i.report_url}">报告</a>`,"操作"]]);document.getElementById("recent-reports").innerHTML=table(payload.recent_reports||[],[[i=>`${text(i.lesson_title)}<br><span class="muted">${sourceLabel(i.dataset_source)}</span>${qualityLine(i.data_quality_note)}`,"报告"],[i=>text(i.score,0),"反馈分"],[i=>riskLabel(i.risk_level),"风险"],[i=>`<a class="button secondary" href="${i.report_url}">打开</a>`,"操作"]]);}
      document.getElementById("filters").addEventListener("submit",e=>{e.preventDefault();const p=new URLSearchParams(new FormData(e.target));[...p.keys()].forEach(k=>{if(!p.get(k))p.delete(k)});window.location.search=p.toString();});
      load().catch(e=>document.getElementById("page-error").textContent=`平台趋势加载失败：${e}`);
    </script>
    """
    return _shell("平台趋势洞察", "trends", "phase30-admin-trends-page", body, current_user)
