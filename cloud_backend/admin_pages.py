"""Admin console pages for V2 Phase 2.7."""
from __future__ import annotations

from typing import Optional


ADMIN_STYLE = """
  <style>
    body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #edf3f8; color: #162033; }
    .page { max-width: 1240px; margin: 0 auto; padding: 22px; }
    .nav { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 18px; border-radius: 20px; background: #172033; color: #fff; box-shadow: 0 18px 42px rgba(15, 23, 42, .18); }
    .nav strong { font-size: 18px; }
    .nav-links { display: flex; flex-wrap: wrap; gap: 9px; }
    .nav a { color: #dbeafe; text-decoration: none; font-weight: 800; padding: 8px 10px; border-radius: 10px; }
    .nav a.active, .nav a:hover { background: rgba(255,255,255,.14); color: #fff; }
    .identity { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; color: #dbeafe; font-size: 13px; }
    .logout { border: 0; border-radius: 10px; padding: 8px 10px; font-weight: 800; cursor: pointer; background: rgba(255,255,255,.16); color: #fff; }
    .badge { display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 900; background: #eef4ff; color: #165dff; }
    .badge.raw { background: #fff7ed; color: #c2410c; }
    .badge.reviewed { background: #ecfdf5; color: #047857; }
    .badge.archived { background: #f3f4f6; color: #4b5563; }
    .hero { margin-top: 18px; padding: 26px; border-radius: 26px; background: radial-gradient(circle at 0 0, #38bdf8, #1d4ed8 36%, #111827); color: #fff; box-shadow: 0 20px 48px rgba(29, 78, 216, .25); }
    .hero .muted { color: #dbeafe; }
    .pipeline { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .pipeline span { background: rgba(255,255,255,.14); border-radius: 999px; padding: 7px 12px; font-weight: 800; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(245px, 1fr)); gap: 16px; margin-top: 18px; }
    .two-col { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(300px, .75fr); gap: 16px; margin-top: 18px; }
    .card { background: rgba(255,255,255,.96); border: 1px solid #d8e6f7; border-radius: 18px; padding: 18px; box-shadow: 0 12px 30px rgba(15, 23, 42, .08); }
    .metric { background: linear-gradient(180deg, #fff, #f6f9ff); border: 1px solid #dbe7ff; border-radius: 16px; padding: 16px; }
    .metric span { display: block; color: #64748b; font-size: 13px; margin-bottom: 8px; }
    .metric strong { font-size: 28px; }
    .muted { color: #64748b; }
    .error { color: #b91c1c; font-weight: 800; }
    .button { display: inline-block; border: 0; border-radius: 12px; padding: 10px 14px; background: #165dff; color: #fff; text-decoration: none; font-weight: 800; cursor: pointer; }
    .button.secondary { background: #eef2f7; color: #172033; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
    th { color: #64748b; font-size: 13px; }
    .filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; }
    label { display: block; color: #64748b; font-size: 13px; margin-bottom: 6px; }
    select, input { min-width: 150px; border: 1px solid #d1d5db; border-radius: 10px; padding: 10px; background: #fff; }
    .empty { border: 1px dashed #cbd5e1; border-radius: 16px; padding: 24px; color: #64748b; background: #f8fafc; }
    .list { display: grid; gap: 12px; }
    .record { border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px; background: #fff; }
    .record-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .kicker { color: #60a5fa; font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
    .status-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .status-row a { text-decoration: none; color: inherit; }
    .pipeline-board { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 18px; }
    .pipeline-step { border: 1px solid rgba(255,255,255,.22); background: rgba(255,255,255,.12); border-radius: 18px; padding: 16px; min-height: 120px; }
    .pipeline-step strong { display: block; font-size: 18px; margin-bottom: 8px; }
    .status-pill { display: inline-block; border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 900; background: #e0f2fe; color: #0369a1; }
    .status-pill.online, .status-pill.ok, .status-pill.ready { background: #dcfce7; color: #166534; }
    .status-pill.stale, .status-pill.warning, .status-pill.inferred { background: #fef3c7; color: #92400e; }
    .status-pill.offline, .status-pill.missing { background: #fee2e2; color: #991b1b; }
    @media (max-width: 860px) { .nav { align-items: flex-start; flex-direction: column; } .two-col { grid-template-columns: 1fr; } table { font-size: 13px; } }
  </style>
"""


def _identity_bar(current_user: Optional[dict]) -> str:
    if not current_user:
        return ""
    display_name = current_user.get("display_name") or current_user.get("username") or "User"
    role = current_user.get("role") or ""
    return f"""
      <div class="identity" data-marker="phase29-user-identity">
        <span>{display_name} · {role}</span>
        <button class="logout" type="button" onclick="fetch('/api/auth/logout', {{method: 'POST'}}).finally(() => window.location.href='/login')">Logout</button>
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
        <strong>Intelligent Classroom Behavior Analysis Platform</strong>
        <span class="badge">Admin Console</span>
      </div>
      <div class="nav-links">
        <a class="{active_class['overview']}" href="/admin">Platform Overview</a>
        <a class="{active_class['classrooms']}" href="/admin/classrooms">Classrooms</a>
        <a class="{active_class['teachers']}" href="/admin/teachers">Teachers</a>
        <a class="{active_class['results']}" href="/admin/results">Classroom Data</a>
        <a class="{active_class['ingestion']}" href="/admin/ingestion">Ingestion Status</a>
        <a href="/teacher">Teacher Console</a>
      </div>
      {_identity_bar(current_user)}
    </nav>
    """


def _shell(title: str, active: str, marker: str, body: str, current_user: Optional[dict] = None) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  {ADMIN_STYLE}
</head>
<body>
  <div class="page" data-marker="{marker}">
    {_admin_nav(active, current_user)}
    {body}
  </div>
</body>
</html>"""


def build_admin_home_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">Admin Console</p>
      <h1>Platform Overview</h1>
      <p class="muted">Global classroom analytics status across capture, local analysis, cloud ingestion, and teacher feedback workflows.</p>
      <div class="pipeline" data-marker="admin-data-pipeline"><span>Capture</span><span>-></span><span>Local Analysis</span><span>-></span><span>Cloud</span><span>-></span><span>Teacher Feedback</span></div>
    </section>
    <p id="page-error" class="error"></p>
    <section id="metric-grid" class="grid" data-marker="admin-overview-metrics"></section>
    <section class="two-col">
      <div class="card">
        <h2>Recent Classroom Analyses</h2>
        <div id="latest-results" class="list" data-marker="admin-latest-results"></div>
      </div>
      <div class="card">
        <h2>Data Ingestion Status</h2>
        <div id="system-status" data-marker="admin-system-status"></div>
        <h2>Status Distribution</h2>
        <div id="status-distribution" class="status-row" data-marker="admin-status-distribution"></div>
      </div>
    </section>
    <section class="card">
      <h2>Quick Links</h2>
      <div id="quick-links" class="grid" data-marker="admin-quick-links"></div>
    </section>
    <script>
      const metricLabels = {
        teacher_count: "Teachers",
        classroom_count: "Classrooms",
        result_count: "Results",
        recent_result_count: "Recent Results",
        today_result_count: "Today",
        raw_count: "Raw",
        reviewed_count: "Reviewed",
        archived_count: "Archived",
        avg_feedback_score: "Avg Feedback",
        avg_attention_score: "Avg Attention",
        avg_response_score: "Avg Response"
      };
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function statusBadge(status) { const safeStatus = status || "raw"; return `<span class="badge ${safeStatus}">${safeStatus}</span>`; }
      async function loadAdminOverview() {
        try {
          const response = await fetch("/api/admin/overview");
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const metrics = payload.metrics || {};
          document.getElementById("metric-grid").innerHTML = Object.entries(metricLabels).map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(metrics[key], 0)}</strong></div>`).join("");
          const status = payload.system_status || {};
          document.getElementById("system-status").innerHTML = `<div class="record"><p><strong>Cloud:</strong> ${text(status.cloud_service)}</p><p><strong>Database:</strong> ${text(status.database)}</p><p><strong>Latest upload:</strong> ${text(status.latest_upload_at)}</p><p><strong>Latest analysis:</strong> ${text(status.latest_analysis_id)}</p><p class="muted">${text(status.latest_raw_path, "")}</p></div>`;
          const distribution = payload.status_distribution || {};
          document.getElementById("status-distribution").innerHTML = ["raw", "reviewed", "archived"].map((name) => `<a class="metric" href="/admin/results?status=${name}"><span>${name}</span><strong>${distribution[name] || 0}</strong></a>`).join("");
          const latest = payload.latest_results || [];
          document.getElementById("latest-results").innerHTML = latest.length ? latest.map((item) => `<div class="record"><div class="record-head"><strong>${text(item.lesson_title)}</strong>${statusBadge(item.status)}</div><p class="muted">${text(item.classroom_name)} / ${text(item.teacher_name)} / ${text(item.created_at || item.generated_at)}</p><p>F ${text(item.feedback_score, 0)} / A ${text(item.attention_score, 0)} / R ${text(item.response_score, 0)}</p><a class="button secondary" href="${item.detail_url}">View Analysis</a></div>`).join("") : `<div class="empty">No classroom analyses yet.</div>`;
          const links = payload.quick_links || [];
          document.getElementById("quick-links").innerHTML = links.map((item) => `<a class="record" href="${item.url}" style="text-decoration:none;color:inherit"><strong>${text(item.label)}</strong><p class="muted">${text(item.description)}</p></a>`).join("");
        } catch (error) {
          document.getElementById("page-error").textContent = `Loading admin overview failed: ${error}`;
        }
      }
      loadAdminOverview();
    </script>
    """
    return _shell("Admin Console", "overview", "admin-overview-page", body, current_user)


def build_admin_classrooms_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">Classroom Overview</p>
      <h1>Classrooms and Recent Activity</h1>
      <p class="muted">Review classroom coverage, teacher mapping, result counts, score averages, and latest active classes.</p>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-classrooms-overview"></section>
    <section class="card">
      <form id="filters" class="filters" data-marker="admin-classrooms-filters">
        <div><label for="q">Search</label><input id="q" name="q" placeholder="classroom or teacher" /></div>
        <div><label for="teacher_id">Teacher ID</label><input id="teacher_id" name="teacher_id" placeholder="demo or numeric id" /></div>
        <button class="button" type="submit">Apply</button>
      </form>
    </section>
    <section class="two-col">
      <div class="card"><h2>Classroom List</h2><div id="classroom-list" data-marker="admin-classroom-list"></div></div>
      <div class="card"><h2>Recently Active / Ranking</h2><div id="ranking" class="list" data-marker="admin-classroom-ranking"></div></div>
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
          document.getElementById("overview").innerHTML = [["classroom_count", "Classrooms"], ["active_classroom_count", "Active"], ["avg_feedback_score", "Avg Feedback"], ["latest_result_at", "Latest Result"]].map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
          const items = payload.items || [];
          document.getElementById("classroom-list").innerHTML = items.length ? `<table><thead><tr><th>Classroom</th><th>Teacher</th><th>Results</th><th>Scores</th><th>Status</th><th>Action</th></tr></thead><tbody>${items.map((item) => `<tr><td>${text(item.classroom_name)}<br><span class="muted">${text(item.classroom_id)}</span></td><td>${text(item.teacher_name)}<br><span class="muted">${text(item.teacher_id)}</span></td><td>${item.result_count || 0}<br><span class="muted">${text(item.latest_result_at)}</span></td><td>F ${text(item.avg_feedback_score, 0)} / A ${text(item.avg_attention_score, 0)} / R ${text(item.avg_response_score, 0)}</td><td>raw ${item.raw_count || 0}<br>reviewed ${item.reviewed_count || 0}<br>archived ${item.archived_count || 0}</td><td><a class="button secondary" href="${item.results_url}">View Results</a></td></tr>`).join("")}</tbody></table>` : `<div class="empty">No classrooms match the current filters.</div>`;
          document.getElementById("ranking").innerHTML = items.slice().sort((a, b) => (b.result_count || 0) - (a.result_count || 0)).slice(0, 6).map((item) => `<div class="record"><strong>${text(item.classroom_name)}</strong><p class="muted">${item.result_count || 0} result(s), avg feedback ${text(item.avg_feedback_score, "N/A")}</p><a class="button secondary" href="${item.results_url}">Open</a></div>`).join("") || `<div class="empty">No ranking data yet.</div>`;
        } catch (error) {
          document.getElementById("page-error").textContent = `Loading classrooms failed: ${error}`;
        }
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      loadClassrooms();
    </script>
    """
    return _shell("Admin Classrooms", "classrooms", "admin-classrooms-page", body, current_user)


def build_admin_teachers_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">Teacher Overview</p>
      <h1>Teachers, Coverage, and Feedback Quality</h1>
      <p class="muted">Review teacher classroom counts, result activity, score averages, and teaching feedback rankings.</p>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-teachers-overview"></section>
    <section class="card"><form id="filters" class="filters" data-marker="admin-teachers-filters"><div><label for="q">Search</label><input id="q" name="q" placeholder="teacher or username" /></div><button class="button" type="submit">Apply</button></form></section>
    <section class="two-col">
      <div class="card"><h2>Teacher List</h2><div id="teacher-list" data-marker="admin-teacher-list"></div></div>
      <div class="card"><h2>Rankings</h2><h3>Classroom Count</h3><div id="classroom-ranking" class="list" data-marker="admin-teacher-classroom-ranking"></div><h3>Average Feedback</h3><div id="feedback-ranking" class="list" data-marker="admin-teacher-feedback-ranking"></div></div>
    </section>
    <script>
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function params() { return new URLSearchParams(window.location.search); }
      function applyForm() { const p = params(); const q = document.getElementById("q"); if (q && p.has("q")) q.value = p.get("q"); }
      function teacherCard(item) { return `<div class="record"><strong>${text(item.teacher_name)}</strong><p class="muted">${text(item.username)} / ${text(item.teacher_id)}</p><p>${item.classroom_count || 0} classroom(s), ${item.result_count || 0} result(s)</p><p>Avg feedback ${text(item.avg_feedback_score, "N/A")}</p><a class="button secondary" href="${item.results_url}">View Results</a></div>`; }
      async function loadTeachers() {
        try {
          applyForm();
          const response = await fetch(`/api/admin/teachers?${params().toString()}`);
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const overview = payload.overview || {};
          document.getElementById("overview").innerHTML = [["teacher_count", "Teachers"], ["teachers_with_classrooms", "With Classrooms"], ["teachers_with_results", "With Results"], ["avg_feedback_score", "Avg Feedback"]].map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
          const items = payload.items || [];
          document.getElementById("teacher-list").innerHTML = items.length ? `<table><thead><tr><th>Teacher</th><th>Coverage</th><th>Scores</th><th>Latest</th><th>Action</th></tr></thead><tbody>${items.map((item) => `<tr><td>${text(item.teacher_name)}<br><span class="muted">${text(item.username)} / ${text(item.teacher_id)}</span></td><td>${item.classroom_count || 0} classroom(s)<br>${item.result_count || 0} result(s)</td><td>F ${text(item.avg_feedback_score, 0)} / A ${text(item.avg_attention_score, 0)} / R ${text(item.avg_response_score, 0)}</td><td>${text(item.latest_result_at)}</td><td><a class="button secondary" href="${item.results_url}">View Results</a></td></tr>`).join("")}</tbody></table>` : `<div class="empty">No teachers match the current filters.</div>`;
          document.getElementById("classroom-ranking").innerHTML = items.slice().sort((a, b) => (b.classroom_count || 0) - (a.classroom_count || 0)).slice(0, 5).map(teacherCard).join("") || `<div class="empty">No classroom ranking yet.</div>`;
          document.getElementById("feedback-ranking").innerHTML = items.slice().sort((a, b) => (b.avg_feedback_score || 0) - (a.avg_feedback_score || 0)).slice(0, 5).map(teacherCard).join("") || `<div class="empty">No feedback ranking yet.</div>`;
        } catch (error) {
          document.getElementById("page-error").textContent = `Loading teachers failed: ${error}`;
        }
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      loadTeachers();
    </script>
    """
    return _shell("Admin Teachers", "teachers", "admin-teachers-page", body, current_user)


def build_admin_results_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">All Classroom Data</p>
      <h1>Platform Classroom Analysis Results</h1>
      <p class="muted">Filter all classroom analyses by classroom, teacher, status, and time range, then jump into the single-session detail.</p>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-results-overview"></section>
    <section class="card">
      <form id="filters" class="filters" data-marker="admin-results-filters">
        <div><label for="classroom_id">Classroom</label><select id="classroom_id" name="classroom_id"><option value="">All classrooms</option></select></div>
        <div><label for="teacher_id">Teacher</label><select id="teacher_id" name="teacher_id"><option value="">All teachers</option></select></div>
        <div><label for="status">Status</label><select id="status" name="status"><option value="">All statuses</option><option value="raw">raw</option><option value="reviewed">reviewed</option><option value="archived">archived</option></select></div>
        <div><label for="days">Time Range</label><select id="days" name="days"><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="all">All</option></select></div>
        <div><label for="limit">Limit</label><input id="limit" name="limit" type="number" min="1" max="100" value="20" /></div>
        <button class="button" type="submit">Apply</button>
      </form>
    </section>
    <section class="two-col">
      <div class="card"><h2>All Results</h2><div id="results-list" data-marker="admin-result-list"></div></div>
      <div class="card"><h2>Status and Tips</h2><div id="status-distribution" class="status-row" data-marker="admin-results-status-distribution"></div><div id="tips" class="list" data-marker="admin-results-tips"></div></div>
    </section>
    <script>
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function statusBadge(status) { const safeStatus = status || "raw"; return `<span class="badge ${safeStatus}">${safeStatus}</span>`; }
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
        classrooms.forEach((item) => { const option = document.createElement("option"); option.value = item.classroom_id || ""; option.textContent = item.classroom_name || item.classroom_id || "unknown"; classroomSelect.appendChild(option); });
        teachers.forEach((item) => { const option = document.createElement("option"); option.value = item.teacher_id || ""; option.textContent = item.teacher_name || item.username || "unknown"; teacherSelect.appendChild(option); });
      }
      async function loadResults() {
        const response = await fetch(`/api/admin/results?${params().toString()}`);
        if (!response.ok) throw new Error(`results HTTP ${response.status}`);
        const payload = await response.json();
        const overview = payload.overview || {};
        document.getElementById("overview").innerHTML = [["result_count", "Total Results"], ["page_count", "Page Results"], ["avg_feedback_score", "Avg Feedback"], ["avg_attention_score", "Avg Attention"], ["low_attention_count", "Low Attention"], ["high_score_count", "High Score"]].map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
        const distribution = overview.status_distribution || {};
        document.getElementById("status-distribution").innerHTML = ["raw", "reviewed", "archived"].map((name) => `<a class="metric" href="/admin/results?status=${name}"><span>${name}</span><strong>${distribution[name] || 0}</strong></a>`).join("");
        const tips = overview.tips || [];
        document.getElementById("tips").innerHTML = tips.map((item) => `<div class="record"><strong>${text(item.title)}</strong><p class="muted">${text(item.description)}</p></div>`).join("");
        const items = payload.items || [];
        document.getElementById("results-list").innerHTML = items.length ? `<table><thead><tr><th>Classroom</th><th>Teacher</th><th>Lesson</th><th>Scores</th><th>Status</th><th>Video</th><th>Action</th></tr></thead><tbody>${items.map((item) => `<tr><td>${text(item.classroom_name)}<br><span class="muted">${text(item.classroom_id)}</span></td><td>${text(item.teacher_name)}<br><span class="muted">${text(item.teacher_id)}</span></td><td>${text(item.lesson_title)}<br><span class="muted">${text(item.created_at || item.generated_at)}</span></td><td>F ${text(item.feedback_score, 0)} / A ${text(item.attention_score, 0)} / R ${text(item.response_score, 0)}</td><td>${statusBadge(item.status)}</td><td>${item.has_video ? "available" : "not available"}<br><span class="muted">${text(item.video_status)}</span></td><td><a class="button secondary" href="${item.detail_url}">View Analysis</a></td></tr>`).join("")}</tbody></table>` : `<div class="empty">No classroom results match the current filters.</div>`;
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      (async function init() { try { await loadFilters(); applyForm(); await loadResults(); } catch (error) { document.getElementById("page-error").textContent = `Loading admin results failed: ${error}`; } })();
    </script>
    """
    return _shell("Admin Results", "results", "admin-results-page", body, current_user)


def build_admin_ingestion_html(current_user: Optional[dict] = None) -> str:
    body = """
    <section class="hero">
      <p class="kicker">Data Ingestion Status</p>
      <h1>Three-Side Data Chain Monitoring</h1>
      <p class="muted">Visualize how classroom sessions move from Raspberry Pi capture, through local analysis, into cloud storage and the teacher feedback dashboard.</p>
      <div id="pipeline" class="pipeline-board" data-marker="admin-ingestion-pipeline"></div>
    </section>
    <p id="page-error" class="error"></p>
    <section id="overview" class="grid" data-marker="admin-ingestion-overview"></section>
    <section class="card">
      <form id="filters" class="filters" data-marker="admin-ingestion-filters">
        <div><label for="classroom_id">Classroom</label><input id="classroom_id" name="classroom_id" placeholder="classroom_101" /></div>
        <div><label for="device_id">Device</label><input id="device_id" name="device_id" placeholder="pi-classroom-101" /></div>
        <div><label for="source_host">Source Host</label><input id="source_host" name="source_host" placeholder="local analyzer host" /></div>
        <div><label for="days">Time Range</label><select id="days" name="days"><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="all">All</option></select></div>
        <div><label for="limit">Limit</label><input id="limit" name="limit" type="number" min="1" max="100" value="20" /></div>
        <button class="button" type="submit">Apply</button>
      </form>
    </section>
    <section class="two-col">
      <div class="card">
        <h2>Device / Analyzer Status</h2>
        <div id="device-list" data-marker="admin-ingestion-devices"></div>
      </div>
      <div class="card">
        <h2>Video Readiness</h2>
        <div id="video-summary" class="status-row" data-marker="admin-ingestion-video-summary"></div>
        <h2>Validation Hints</h2>
        <div id="validation-hints" class="list" data-marker="admin-ingestion-validation-hints"></div>
      </div>
    </section>
    <section class="card">
      <h2>Recent Ingestion Records</h2>
      <div id="recent-ingestions" data-marker="admin-ingestion-recent"></div>
    </section>
    <script>
      function text(value, fallback = "N/A") { return value === null || value === undefined || value === "" ? fallback : value; }
      function params() { return new URLSearchParams(window.location.search); }
      function statusPill(value) { const safe = value || "unknown"; return `<span class="status-pill ${safe}">${safe}</span>`; }
      function applyForm() { const p = params(); ["classroom_id", "device_id", "source_host", "days", "limit"].forEach((key) => { const el = document.getElementById(key); if (el && p.has(key)) el.value = p.get(key); }); }
      async function loadIngestion() {
        try {
          applyForm();
          const response = await fetch(`/api/admin/ingestion?${params().toString()}`);
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          const overview = payload.overview || {};
          const metricLabels = [
            ["total_results", "Ingested Results"],
            ["active_devices", "Online Devices"],
            ["stale_devices", "Stale Devices"],
            ["offline_devices", "Offline Devices"],
            ["playable_videos", "Playable Videos"],
            ["pending_videos", "Pending Videos"],
            ["missing_videos", "Missing Videos"],
            ["metadata_complete_rate", "Metadata Complete %"]
          ];
          document.getElementById("overview").innerHTML = metricLabels.map(([key, label]) => `<div class="metric"><span>${label}</span><strong>${text(overview[key], 0)}</strong></div>`).join("");
          const pipeline = payload.pipeline || [];
          document.getElementById("pipeline").innerHTML = pipeline.map((item) => `<div class="pipeline-step"><strong>${text(item.stage)}</strong>${statusPill(item.status)}<p>${text(item.count, 0)} session(s)</p><p class="muted">${text(item.description)}</p></div>`).join("");
          const devices = payload.devices || [];
          document.getElementById("device-list").innerHTML = devices.length ? `<table><thead><tr><th>Device</th><th>Classroom</th><th>Source</th><th>Latest Upload</th><th>Status</th><th>Video</th></tr></thead><tbody>${devices.map((item) => `<tr><td>${text(item.device_name)}<br><span class="muted">${text(item.device_id)}</span></td><td>${text(item.classroom_id)}</td><td>${text(item.source_host)}</td><td>${text(item.latest_upload_time)}<br><span class="muted">${item.total_sessions || 0} session(s)</span></td><td>${statusPill(item.freshness)}<br><span class="muted">${text(item.metadata_quality)}</span></td><td>${statusPill(item.video_status)}<br><span class="muted">standardized: ${item.standardized_video_present ? "yes" : "no"}</span><br><span class="muted">browser: ${item.browser_compatible === true ? "compatible" : item.browser_compatible === false ? "incompatible" : "unknown"}</span></td></tr>`).join("")}</tbody></table>` : `<div class="empty">No device/source status is available for current filters.</div>`;
          const video = payload.video_summary || {};
          document.getElementById("video-summary").innerHTML = ["playable", "pending", "missing", "unknown", "standardized_present", "browser_compatible", "browser_incompatible", "transcode_failed"].map((name) => `<div class="metric"><span>${name}</span><strong>${video[name] || 0}</strong></div>`).join("");
          const hints = payload.validation_hints || [];
          document.getElementById("validation-hints").innerHTML = hints.map((item) => `<div class="record"><div class="record-head"><strong>${text(item.type)}</strong>${statusPill(item.severity)}</div><p class="muted">${text(item.message)}</p></div>`).join("") || `<div class="empty">No validation hints.</div>`;
          const recent = payload.recent_ingestions || [];
          document.getElementById("recent-ingestions").innerHTML = recent.length ? `<table><thead><tr><th>Result</th><th>Classroom</th><th>Device</th><th>Source</th><th>Times</th><th>Metadata</th><th>Video Standardization</th><th>Action</th></tr></thead><tbody>${recent.map((item) => `<tr><td>${text(item.lesson_title)}<br><span class="muted">${text(item.result_id)}</span></td><td>${text(item.classroom_id)}</td><td>${text(item.device_id)}</td><td>${text(item.source_host)}</td><td>Capture: ${text(item.capture_time)}<br>Upload: ${text(item.upload_time)}</td><td>${statusPill(item.video_status)}<br><span class="muted">${text(item.metadata_status)}</span></td><td>standardized: ${item.standardized_video_present ? "yes" : "no"}<br>browser: ${item.browser_compatible === true ? "compatible" : item.browser_compatible === false ? "incompatible" : "unknown"}<br>transcode: ${text(item.transcode_status)}<br><span class="muted">${text(item.transcode_error, "")}</span></td><td><a class="button secondary" href="${item.detail_url}">Open Dashboard</a></td></tr>`).join("")}</tbody></table>` : `<div class="empty">No ingestion records match the current filters.</div>`;
        } catch (error) {
          document.getElementById("page-error").textContent = `Loading ingestion status failed: ${error}`;
        }
      }
      document.getElementById("filters").addEventListener("submit", (event) => { event.preventDefault(); const p = new URLSearchParams(new FormData(event.target)); [...p.keys()].forEach((key) => { if (!p.get(key)) p.delete(key); }); window.location.search = p.toString(); });
      loadIngestion();
    </script>
    """
    return _shell("Admin Ingestion Status", "ingestion", "admin-ingestion-page", body, current_user)
