"""Teacher home and classroom records pages for V2 Phase 2.6."""
from __future__ import annotations


BASE_STYLE = """
  <style>
    body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #eef4fb; color: #172033; }
    .page { max-width: 1220px; margin: 0 auto; padding: 22px; }
    .nav { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 18px; border-radius: 18px; background: #0f172a; color: #fff; box-shadow: 0 16px 34px rgba(15, 23, 42, .18); }
    .nav strong { font-size: 18px; }
    .nav-links { display: flex; gap: 10px; flex-wrap: wrap; }
    .nav a { color: #dbeafe; text-decoration: none; font-weight: 700; padding: 8px 10px; border-radius: 10px; }
    .nav a.active, .nav a:hover { background: rgba(255,255,255,.14); color: #fff; }
    .badge { display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 800; background: #eef4ff; color: #165dff; }
    .badge.raw { background: #fff7ed; color: #c2410c; }
    .badge.reviewed { background: #ecfdf5; color: #047857; }
    .badge.archived { background: #f3f4f6; color: #4b5563; }
    .hero { margin-top: 18px; padding: 24px; border-radius: 24px; background: linear-gradient(135deg, #1d4ed8, #0f172a); color: #fff; box-shadow: 0 18px 44px rgba(29, 78, 216, .24); }
    .hero .muted { color: #dbeafe; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 18px; }
    .card { background: rgba(255,255,255,.96); border: 1px solid #dbe7ff; border-radius: 18px; padding: 18px; box-shadow: 0 12px 30px rgba(15, 23, 42, .08); }
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
    select, input { min-width: 160px; border: 1px solid #d1d5db; border-radius: 10px; padding: 10px; background: #fff; }
    .empty { border: 1px dashed #cbd5e1; border-radius: 16px; padding: 24px; color: #64748b; background: #f8fafc; }
    .list { display: grid; gap: 12px; }
    .record { border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px; background: #fff; }
    .record-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .kicker { color: #165dff; font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
    @media (max-width: 760px) { .nav { align-items: flex-start; flex-direction: column; } table { font-size: 13px; } }
  </style>
"""


def _teacher_nav(active: str) -> str:
    home_class = "active" if active == "home" else ""
    results_class = "active" if active == "results" else ""
    detail_class = "active" if active == "detail" else ""
    return f"""
    <nav class="nav" data-marker="teacher-console-nav">
      <div>
        <strong>Intelligent Classroom Behavior Analysis Platform</strong>
        <span class="badge">Teacher Console</span>
      </div>
      <div class="nav-links">
        <a class="{home_class}" href="/teacher">Home</a>
        <a class="{results_class}" href="/teacher/results">Classroom Records</a>
        <a class="{detail_class}" href="/dashboard">Analysis Detail</a>
      </div>
    </nav>
    """


def build_teacher_home_html() -> str:
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Teacher Console</title>
  __BASE_STYLE__
</head>
<body>
  <div class="page" data-marker="teacher-home-page">
    __TEACHER_NAV__
    <section class="hero">
      <p class="kicker">Teacher Console</p>
      <h1 id="welcome-title">Welcome back, Teacher</h1>
      <p class="muted">Capture -> Local Analysis -> Cloud. Review recent classroom behavior analysis and jump into the session that needs attention.</p>
      <p class="muted">Last data update: <span id="last-update">Loading...</span></p>
      <a class="button" href="/teacher/results">Enter Classroom Records</a>
    </section>
    <p id="page-error" class="error"></p>
    <section class="grid" id="metric-grid" data-marker="teacher-home-metrics"></section>
    <section class="grid">
      <div class="card">
        <h2>Recent Classroom Analyses</h2>
        <div id="latest-results" class="list" data-marker="teacher-home-latest"></div>
      </div>
      <div class="card">
        <h2>Todo / Teaching Tips</h2>
        <div id="todo-items" class="list" data-marker="teacher-home-todos"></div>
      </div>
    </section>
    <section class="card">
      <h2>Classroom Overview</h2>
      <div id="classroom-summaries" class="grid" data-marker="teacher-home-classrooms"></div>
    </section>
  </div>
  <script>
    const metricLabels = {
      classroom_count: "Classrooms",
      total_result_count: "Total Results",
      recent_result_count: "Recent Results",
      raw_count: "Pending Review",
      reviewed_count: "Reviewed",
      archived_count: "Archived",
      avg_feedback_score: "Avg Feedback",
      avg_attention_score: "Avg Attention",
      avg_response_score: "Avg Response"
    };

    function text(value, fallback = "N/A") {
      return value === null || value === undefined || value === "" ? fallback : value;
    }

    function statusBadge(status) {
      const safeStatus = status || "raw";
      return `<span class="badge ${safeStatus}">${safeStatus}</span>`;
    }

    async function loadTeacherHome() {
      try {
        const response = await fetch("/api/teacher/overview");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        const teacher = payload.teacher || {};
        const metrics = payload.metrics || {};
        document.getElementById("welcome-title").textContent = `Welcome back, ${teacher.display_name || teacher.username || "Demo Teacher"}`;
        const latest = payload.latest_results || [];
        document.getElementById("last-update").textContent = latest[0]?.created_at || latest[0]?.generated_at || "No classroom data yet";
        document.getElementById("metric-grid").innerHTML = Object.entries(metricLabels).map(([key, label]) => `
          <div class="metric"><span>${label}</span><strong>${text(metrics[key], 0)}</strong></div>
        `).join("");
        document.getElementById("latest-results").innerHTML = latest.length ? latest.map((item) => `
          <div class="record">
            <div class="record-head"><strong>${text(item.lesson_title)}</strong>${statusBadge(item.status)}</div>
            <p class="muted">${text(item.classroom_name)} · ${text(item.created_at || item.generated_at)}</p>
            <p>Feedback ${text(item.feedback_score, 0)} · Attention ${text(item.attention_score, 0)} · Response ${text(item.response_score, 0)}</p>
            <a class="button secondary" href="${item.detail_url}">View Analysis</a>
          </div>
        `).join("") : `<div class="empty">No classroom analyses yet.</div>`;
        const todos = payload.todo_items || [];
        document.getElementById("todo-items").innerHTML = todos.length ? todos.map((item) => `
          <a class="record" href="${item.target_url || "/teacher/results"}" style="text-decoration:none;color:inherit">
            <strong>${text(item.title)}</strong>
            <p class="muted">${text(item.description)}</p>
          </a>
        `).join("") : `<div class="empty">No pending teaching tips.</div>`;
        const classrooms = payload.classroom_summaries || [];
        document.getElementById("classroom-summaries").innerHTML = classrooms.length ? classrooms.map((item) => `
          <div class="record">
            <strong>${text(item.classroom_name)}</strong>
            <p class="muted">${item.result_count || 0} result(s) · latest ${text(item.latest_result_at)}</p>
            <p>Avg feedback: ${text(item.avg_feedback_score, "N/A")}</p>
            <a class="button secondary" href="${item.records_url}">View Records</a>
          </div>
        `).join("") : `<div class="empty">No classroom summaries yet.</div>`;
      } catch (error) {
        document.getElementById("page-error").textContent = `Loading teacher overview failed: ${error}`;
      }
    }
    loadTeacherHome();
  </script>
</body>
</html>"""
    return template.replace("__BASE_STYLE__", BASE_STYLE).replace("__TEACHER_NAV__", _teacher_nav("home"))


def build_teacher_results_html() -> str:
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Classroom Records</title>
  __BASE_STYLE__
</head>
<body>
  <div class="page" data-marker="teacher-results-page">
    __TEACHER_NAV__
    <section class="hero">
      <p class="kicker">Classroom Records</p>
      <h1>Find the classroom session to analyze</h1>
      <p class="muted">Filter by classroom, review status, and time range, then open the Phase 2.5 analysis detail.</p>
    </section>
    <section class="card">
      <form id="filters" class="filters" data-marker="teacher-results-filters">
        <div>
          <label for="classroom_id">Classroom</label>
          <select id="classroom_id" name="classroom_id"><option value="">All classrooms</option></select>
        </div>
        <div>
          <label for="status">Status</label>
          <select id="status" name="status">
            <option value="">All statuses</option>
            <option value="raw">raw</option>
            <option value="reviewed">reviewed</option>
            <option value="archived">archived</option>
          </select>
        </div>
        <div>
          <label for="days">Time Range</label>
          <select id="days" name="days">
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="all">All</option>
          </select>
        </div>
        <div>
          <label for="limit">Limit</label>
          <input id="limit" name="limit" type="number" min="1" max="100" value="20" />
        </div>
        <button class="button" type="submit">Apply</button>
      </form>
    </section>
    <p id="page-error" class="error"></p>
    <section class="card">
      <h2>Classroom Records <span class="muted" id="total-count"></span></h2>
      <div id="records" data-marker="teacher-results-list"></div>
    </section>
  </div>
  <script>
    function text(value, fallback = "N/A") {
      return value === null || value === undefined || value === "" ? fallback : value;
    }
    function statusBadge(status) {
      const safeStatus = status || "raw";
      return `<span class="badge ${safeStatus}">${safeStatus}</span>`;
    }
    function currentParams() {
      const params = new URLSearchParams(window.location.search);
      return params;
    }
    function applyParamsToForm() {
      const params = currentParams();
      ["classroom_id", "status", "days", "limit"].forEach((key) => {
        const el = document.getElementById(key);
        if (el && params.has(key)) el.value = params.get(key);
      });
    }
    async function loadClassrooms() {
      const response = await fetch("/api/teacher/classrooms");
      if (!response.ok) throw new Error(`classrooms HTTP ${response.status}`);
      const payload = await response.json();
      const select = document.getElementById("classroom_id");
      const current = currentParams().get("classroom_id") || "";
      (payload.items || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = item.classroom_id || "";
        option.textContent = item.classroom_name || item.classroom_id || "unknown";
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
      document.getElementById("total-count").textContent = `(${payload.total || 0} total)`;
      document.getElementById("records").innerHTML = items.length ? `
        <table>
          <thead><tr><th>Classroom</th><th>Lesson</th><th>Time</th><th>Scores</th><th>Status</th><th>Video</th><th>Action</th></tr></thead>
          <tbody>${items.map((item) => `
            <tr>
              <td>${text(item.classroom_name)}<br><span class="muted">${text(item.classroom_id)}</span></td>
              <td>${text(item.lesson_title)}<br><span class="muted">${text(item.analysis_id)}</span></td>
              <td>Recorded: ${text(item.recorded_at)}<br>Generated: ${text(item.generated_at)}<br>Created: ${text(item.created_at)}</td>
              <td>F ${text(item.feedback_score, 0)} / A ${text(item.attention_score, 0)} / R ${text(item.response_score, 0)}</td>
              <td>${statusBadge(item.status)}</td>
              <td>${item.has_video ? "available" : "not available"}<br><span class="muted">${text(item.video_status)}</span></td>
              <td><a class="button secondary" href="${item.detail_url}">View Analysis</a></td>
            </tr>
          `).join("")}</tbody>
        </table>` : `<div class="empty">No classroom records match the current filters.</div>`;
    }
    document.getElementById("filters").addEventListener("submit", (event) => {
      event.preventDefault();
      const params = new URLSearchParams(new FormData(event.target));
      [...params.keys()].forEach((key) => { if (!params.get(key)) params.delete(key); });
      window.location.search = params.toString();
    });
    (async function init() {
      try {
        applyParamsToForm();
        await loadClassrooms();
        applyParamsToForm();
        await loadRecords();
      } catch (error) {
        document.getElementById("page-error").textContent = `Loading classroom records failed: ${error}`;
      }
    })();
  </script>
</body>
</html>"""
    return template.replace("__BASE_STYLE__", BASE_STYLE).replace("__TEACHER_NAV__", _teacher_nav("results"))
