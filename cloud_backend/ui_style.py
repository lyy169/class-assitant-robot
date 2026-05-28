"""Shared Phase 3.1 visual tokens for cloud HTML pages."""
from __future__ import annotations


PHASE31_STYLE = """
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    :root {
      --color-bg: #F5F7FB;
      --color-surface: #FFFFFF;
      --color-surface-soft: #F8FAFC;
      --color-surface-tint: #EEF6FF;
      --color-border: #DDE5F0;
      --color-border-soft: #E8EEF6;
      --color-text: #102033;
      --color-text-muted: #5F6F86;
      --color-text-subtle: #8A98AA;
      --color-primary: #2563EB;
      --color-primary-strong: #1D4ED8;
      --color-primary-soft: #E8F1FF;
      --color-secondary: #14B8A6;
      --color-secondary-soft: #DDFBF5;
      --color-teaching: #7C3AED;
      --color-teaching-soft: #F0E9FF;
      --color-warm: #F59E0B;
      --color-warm-soft: #FFF4D6;
      --color-success: #10B981;
      --color-success-soft: #E8FFF6;
      --color-warning: #F59E0B;
      --color-warning-soft: #FFF7E6;
      --color-danger: #EF4444;
      --color-danger-soft: #FFF0F0;
      --color-info: #0EA5E9;
      --color-info-soft: #E7F7FF;
      --chart-attention: #2563EB;
      --chart-activity: #14B8A6;
      --chart-question: #F59E0B;
      --chart-stage-summary: #7C3AED;
      --chart-stage-discussion: #06B6D4;
      --chart-stage-exposition: #3B82F6;
      --chart-stage-management: #94A3B8;
      --chart-risk: #EF4444;
      --chart-neutral: #64748B;
      --radius-card: 8px;
      --radius-media: 10px;
      --radius-button: 8px;
      --radius-chip: 999px;
      --sidebar-width: 240px;
      --topbar-height: 72px;
      --page-pad-x: 28px;
      --page-pad-y: 24px;
      --section-gap: 24px;
      --grid-gap: 18px;
      --shadow: 0 10px 28px rgba(16, 32, 51, 0.07);
      --shadow-hover: 0 14px 36px rgba(16, 32, 51, 0.11);
      --bg: var(--color-bg);
      --panel: var(--color-surface);
      --line: var(--color-border);
      --text: var(--color-text);
      --muted: var(--color-text-muted);
      --brand: var(--color-primary);
      --brand-2: var(--color-secondary);
      --attention: var(--chart-attention);
      --activity: var(--chart-activity);
      --question: var(--chart-question);
      --risk: var(--chart-risk);
      --success: var(--color-success);
      --warning: var(--color-warning);
      --danger: var(--color-danger);
      --slate: var(--chart-neutral);
    }
    html { width: 100%; min-height: 100%; overflow-y: auto; }
    body {
      margin: 0;
      width: 100%;
      min-height: 100%;
      overflow-y: auto;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
      background:
        linear-gradient(180deg, rgba(232,241,255,.72), rgba(245,247,251,.5) 310px, var(--color-bg) 680px),
        radial-gradient(circle at 18px 18px, rgba(37,99,235,.055) 1px, transparent 1.6px),
        var(--color-bg);
      background-size: auto, 28px 28px, auto;
      color: var(--text);
      font-size: 14px;
      line-height: 1.65;
    }
    h1, h2, h3, p { overflow-wrap: anywhere; }
    h1 { font-size: 28px; line-height: 1.25; font-weight: 700; margin: 0 0 10px; letter-spacing: 0; }
    h2 { font-size: 20px; line-height: 1.3; font-weight: 700; margin: 0 0 12px; }
    h3 { font-size: 16px; line-height: 1.35; font-weight: 700; margin: 0 0 10px; }
    .page, .app-shell { width: 100%; max-width: 1480px; margin: 0 auto; padding: var(--page-pad-y) var(--page-pad-x); overflow: visible; }
    .page:has(> .nav) {
      max-width: none;
      min-height: 100vh;
      display: grid;
      grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
      align-items: start;
      column-gap: 24px;
    }
    .page:has(> .nav) > :not(.nav) { grid-column: 2; min-width: 0; width: 100%; }
    .page-main { display: grid; gap: var(--section-gap); width: 100%; min-width: 0; }
    .nav {
      display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; gap: 18px;
      min-height: calc(100vh - 48px);
      padding: 18px 14px; border-radius: var(--radius-card); background: linear-gradient(180deg, #ffffff, #f8fbff);
      border: 1px solid var(--color-border); box-shadow: var(--shadow);
      position: sticky; top: 24px; z-index: 20;
      width: 100%;
    }
    .page:has(> .nav) > .nav { grid-column: 1; grid-row: 1 / span 999; }
    .nav strong { display: block; font-size: 16px; line-height: 1.35; letter-spacing: 0; color: #0f172a; margin-bottom: 8px; }
    .nav strong::before { content: "▦"; display: inline-grid; place-items: center; width: 30px; height: 30px; margin-right: 8px; border-radius: 8px; background: var(--color-primary); color: #fff; font-size: 16px; vertical-align: middle; }
    .nav-links { display: flex; flex-direction: column; gap: 6px; }
    .nav a {
      color: #334155; text-decoration: none; font-weight: 700; padding: 10px 12px;
      border-radius: var(--radius-button); transition: .18s ease;
    }
    .nav a.active, .nav a:hover { background: var(--color-primary-soft); color: var(--color-primary-strong); }
    .identity { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; color: var(--muted); font-size: 13px; }
    .nav .identity { margin-top: auto; padding-top: 12px; border-top: 1px solid var(--color-border-soft); }
    .logout { border: 0; border-radius: var(--radius-button); padding: 8px 12px; font-weight: 700; cursor: pointer; background: #102033; color: #fff; }
    .badge, .status-pill {
      display: inline-flex; align-items: center; min-height: 24px; border-radius: var(--radius-chip); padding: 0 10px; font-size: 12px;
      font-weight: 600; background: var(--color-primary-soft); color: var(--brand);
    }
    .badge.raw, .status-pill.warning, .badge.medium { background: #fff7ed; color: var(--warning); }
    .badge.reviewed, .badge.low, .status-pill.online, .status-pill.ok, .status-pill.ready { background: #ecfdf5; color: var(--success); }
    .badge.archived, .badge.unknown { background: #f1f5f9; color: var(--slate); }
    .badge.high, .status-pill.offline, .status-pill.missing { background: #fee2e2; color: var(--danger); }
    .hero, .page-header, .top-context {
      min-height: var(--topbar-height);
      padding: 18px 22px; border-radius: var(--radius-card);
      background: var(--color-surface);
      border: 1px solid var(--color-border); box-shadow: var(--shadow); color: var(--text);
      position: relative;
      overflow: clip;
    }
    .hero::after, .page-header::after, .top-context::after {
      content: "";
      position: absolute;
      right: 18px;
      top: 18px;
      width: 160px;
      height: 72px;
      pointer-events: none;
      opacity: .45;
      background:
        linear-gradient(90deg, rgba(37,99,235,.12) 1px, transparent 1px),
        linear-gradient(180deg, rgba(20,184,166,.14) 1px, transparent 1px);
      background-size: 18px 18px;
      mask-image: linear-gradient(90deg, transparent, #000 28%, #000);
    }
    .hero .muted { color: var(--muted); }
    .hero h1 { font-size: 28px; line-height: 1.25; }
    .kicker { color: var(--brand); font-size: 12px; font-weight: 600; letter-spacing: 0; }
    .grid, .metric-grid, .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--grid-gap); margin-top: var(--section-gap); min-width: 0; }
    .metric-grid, #metric-grid, #overview { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .record-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; min-width: 0; }
    .chart-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; margin-top: var(--section-gap); min-width: 0; }
    .two-col, .dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; margin-top: var(--section-gap); align-items: start; min-width: 0; }
    .chart-side-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(320px, .85fr); gap: 20px; margin-top: var(--section-gap); min-width: 0; }
    .dashboard-main, .dashboard-side { min-width: 0; display: grid; gap: 16px; align-content: start; }
    .dashboard-wide { grid-column: 1 / -1; }
    .card, .chart-panel, .insight-panel, .evidence-panel, .report-card, .action-card, .result-card {
      background: var(--panel); border: 1px solid #E2E8F0; border-radius: var(--radius-card); padding: 20px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, .06); min-width: 0; overflow-wrap: anywhere;
      animation: phase31b-rise .42s ease both;
    }
    .evidence-panel { background: linear-gradient(145deg, #0f172a, #163364); color: #eef6ff; }
    .evidence-panel .muted { color: #bfdbfe; }
    .insight-panel { background: linear-gradient(135deg, #f8fbff, #ffffff); border-left: 4px solid var(--brand); }
    .action-card { border-left: 4px solid var(--question); }
    .card:hover, .report-card:hover, .action-card:hover { transform: translateY(-1px); box-shadow: var(--shadow-hover); }
    .metric { background: var(--color-surface); border: 1px solid #E2E8F0; border-radius: var(--radius-card); padding: 18px; min-height: 112px; position: relative; overflow: clip; }
    .metric::before { content: ""; position: absolute; left: 18px; top: 14px; width: 26px; height: 4px; border-radius: 999px; background: linear-gradient(90deg, var(--color-primary), var(--color-secondary)); }
    .metric span { display: block; color: var(--muted); font-size: 13px; font-weight: 600; margin-bottom: 8px; }
    .metric strong, .metric-value { font-size: 32px; font-weight: 750; color: #0f172a; line-height: 1.05; }
    .muted { color: var(--muted); }
    .error { color: var(--danger); font-weight: 800; }
    .button, button, .link-button {
      display: inline-block; border: 0; border-radius: var(--radius-button); padding: 10px 14px;
      background: var(--brand); color: #fff; text-decoration: none; font-weight: 700; cursor: pointer;
      white-space: nowrap; transition: .18s ease;
    }
    .button.secondary, .link-button, .action-button { background: #eef4fb; color: #172033; }
    .danger-light { background: #fff7ed; color: #c2410c; }
    .table-scroll { width: 100%; max-width: 100%; overflow-x: auto; overflow-y: visible; border-radius: 16px; }
    table { width: 100%; border-collapse: collapse; min-width: 760px; }
    th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid #e5edf6; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; font-weight: 700; background: var(--color-surface-soft); }
    .filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; }
    label { display: block; color: var(--muted); font-size: 13px; margin-bottom: 6px; font-weight: 800; }
    select, input { min-width: 150px; border: 1px solid #cbd5e1; border-radius: var(--radius-button); padding: 10px; background: #fff; }
    .empty { border: 1px dashed #cbd5e1; border-radius: var(--radius-card); padding: 22px; color: var(--muted); background: #f8fafc; }
    .list { display: grid; gap: 12px; }
    .record, .result-card { border: 1px solid #e5edf6; border-radius: var(--radius-card); padding: 14px; background: #fff; min-width: 0; }
    .record-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .action-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    td .button, td button, td .action-button { margin: 2px 4px 2px 0; }
    .pipeline { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .pipeline span { background: #e8f1ff; color: #1d4ed8; border-radius: 999px; padding: 7px 12px; font-weight: 900; }
    .chart, .chart-box { height: 320px; min-height: 300px; width: 100%; }
    .chart-hero { height: 380px; min-height: 360px; }
    .warning { background: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; border-radius: 16px; padding: 12px; margin-top: 14px; }
    .insight-card { background: linear-gradient(135deg, #f8fbff, #ffffff); border-left: 4px solid var(--brand); }
    .data-strip, .timeline-strip, .heat-strip { display: grid; grid-template-columns: repeat(12, 1fr); gap: 4px; margin: 12px 0; }
    .strip-cell { height: 22px; border-radius: 7px; background: #dbeafe; position: relative; overflow: hidden; }
    .strip-cell.low { background: #fee2e2; }
    .strip-cell.medium { background: #fef3c7; }
    .strip-cell.high { background: #dcfce7; }
    .strip-cell.question::after { content: ""; position: absolute; inset: 4px; border-radius: 999px; background: var(--question); opacity: .9; }
    .flow-board { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin-top: 16px; }
    .flow-step { border: 1px solid rgba(37,99,235,.18); border-radius: var(--radius-card); padding: 16px; background: rgba(255,255,255,.82); position: relative; min-width: 0; }
    .flow-step::before { content: ""; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; background: var(--success); box-shadow: 0 0 0 5px rgba(22,163,74,.12); }
    .flow-step.warning::before, .flow-step.stale::before, .flow-step.inferred::before { background: var(--warning); box-shadow: 0 0 0 5px rgba(217,119,6,.12); }
    .flow-step.missing::before, .flow-step.offline::before, .flow-step.failed::before { background: var(--danger); box-shadow: 0 0 0 5px rgba(220,38,38,.12); }
    .progress-track { height: 10px; border-radius: 999px; background: #e2e8f0; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--brand), var(--activity)); }
    .rank-bar { display: grid; gap: 8px; }
    .rank-item { display: grid; grid-template-columns: minmax(0,1fr) 82px; gap: 10px; align-items: center; }
    .rank-line { height: 10px; border-radius: 999px; background: #e2e8f0; overflow: hidden; }
    .rank-line span { display: block; height: 100%; background: linear-gradient(90deg, var(--brand), var(--brand-2)); }
    .large-score { font-size: 52px; line-height: 1; font-weight: 800; color: var(--color-primary-strong); }
    .insight-item { padding: 14px; border-radius: var(--radius-card); background: var(--color-surface-soft); border: 1px solid var(--color-border-soft); }
    .visual-badge { display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border-radius: var(--radius-chip); background: rgba(255,255,255,.86); color: var(--color-text); font-size: 12px; font-weight: 700; box-shadow: var(--shadow); }
    .context-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; position: relative; z-index: 1; }
    .context-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .hero > *, .page-header > *, .top-context > * { position: relative; z-index: 1; }
    .section-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; }
    .panel-note { color: var(--muted); font-size: 13px; margin: -4px 0 12px; }
    .split-visual { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: stretch; min-width: 0; }
    .teaching-hero { min-height: 280px; display: grid; align-content: center; }
    .priority-list { display: grid; gap: 10px; }
    .priority-card { display: grid; gap: 6px; padding: 14px; border-radius: var(--radius-card); background: var(--color-surface-soft); border: 1px solid var(--color-border-soft); }
    .result-card { display: grid; gap: 10px; min-height: 178px; transition: .18s ease; }
    .result-card:hover { transform: translateY(-1px); box-shadow: var(--shadow-hover); }
    .result-card .score-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
    .mini-stat { border-radius: 8px; padding: 9px 10px; background: var(--color-surface-soft); border: 1px solid var(--color-border-soft); }
    .mini-stat span { display: block; color: var(--muted); font-size: 12px; font-weight: 700; }
    .mini-stat strong { display: block; font-size: 18px; line-height: 1.2; }
    .evidence-split { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; min-width: 0; }
    .evidence-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    .insight-stack { display: grid; gap: 12px; }
    .login-visual-panel { position: relative; min-height: 640px; border-radius: 24px; overflow: hidden; border: 1px solid rgba(221,229,240,.78); box-shadow: var(--shadow); background: linear-gradient(135deg, rgba(16,32,51,.28), rgba(37,99,235,.16)), var(--login-image, linear-gradient(135deg, #dbeafe, #ecfeff)); background-size: cover; background-position: center; }
    .login-visual-panel::after { content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(16,32,51,.05), rgba(16,32,51,.56)); }
    .login-product-card { display: grid; align-content: center; min-height: 640px; }
    details.debug-details { border: 1px solid var(--line); border-radius: var(--radius-card); padding: 14px; background: #fff; overflow: visible; }
    details.debug-details > .detail-box, .detail-box { max-height: 420px; overflow: auto; }
    @keyframes phase31b-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
    @media (max-width: 860px) {
      .page:has(> .nav) { display: block; padding: 14px; }
      .nav { position: relative; top: auto; min-height: auto; margin-bottom: 16px; align-items: flex-start; flex-direction: column; }
      .nav-links { flex-direction: row; flex-wrap: wrap; }
      .two-col, .dashboard-grid, .chart-side-grid, .flow-board { grid-template-columns: 1fr; }
      .split-visual, .evidence-split { grid-template-columns: 1fr; }
      .chart-grid, .metric-grid, #metric-grid, #overview { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
      .login-visual-panel, .login-product-card { min-height: auto; }
      table { font-size: 13px; }
      .page, .app-shell { padding: 14px; }
    }
  </style>
"""


def role_label(role: str) -> str:
    return {"admin": "管理员", "teacher": "教师"}.get(role or "", role or "用户")


def status_label(status: str) -> str:
    return {
        "raw": "待复盘",
        "reviewed": "已复盘",
        "archived": "已归档",
        "ok": "正常",
        "ready": "就绪",
        "success": "成功",
        "failed": "失败",
        "missing": "缺失",
        "partial": "部分完整",
        "complete": "完整",
        "inferred": "推断",
        "stale": "可能过期",
        "online": "在线",
        "offline": "离线",
        "unknown": "未知",
    }.get(status or "", status or "未知")


def risk_label(risk: str) -> str:
    return {"high": "高风险", "medium": "中风险", "low": "低风险", "unknown": "未知"}.get(risk or "", risk or "未知")


def data_source_label(source: str) -> str:
    return {"real": "真实数据", "demo": "演示数据", "all": "全部数据"}.get(source or "", source or "未知")


def ingestion_status_label(status: str) -> str:
    return status_label(status)


def video_status_label(status: str) -> str:
    return {"playable": "可播放", "pending": "待接入", "missing": "缺失", "unknown": "未知"}.get(status or "", status or "未知")
