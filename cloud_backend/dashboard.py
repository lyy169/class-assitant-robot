"""Helpers for reading and rendering classroom interaction results."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from .storage import FileResultRepository


def latest_result_or_404(
    repository: FileResultRepository,
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
) -> str:
    latest_summary = _result_summary(latest_payload)
    latest_summary["source_kind"] = latest_source_kind
    latest_summary["source_path"] = str(latest_source_path)

    filter_value = html.escape(classroom_id or "")
    result_source_note = (
        "Current data comes from received JSON files."
        if latest_source_kind == "raw"
        else "Current data falls back to sample JSON because no raw classroom result is available yet."
    )

    recent_rows = "".join(_recent_result_row(result) for result in recent_results)
    if not recent_rows:
        recent_rows = '<tr><td colspan="6">No classroom results are available yet.</td></tr>'

    heat_items = _render_heat_items(latest_payload.get("grid_stats") or {})
    latest_counts_items = _render_interaction_items(latest_payload.get("interaction_counts") or {})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cloud Classroom Results Center</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --line: #d8e0ea;
      --text: #1c2734;
      --muted: #617083;
      --accent: #165dff;
      --soft: #eef4ff;
      --warm: #fef3c7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #eef4ff 0%, var(--bg) 220px);
      color: var(--text);
    }}
    .page {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }}
    .hero {{
      display: grid;
      gap: 18px;
      margin-bottom: 20px;
    }}
    .hero-card, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
      padding: 20px;
    }}
    .hero-card {{
      background: linear-gradient(135deg, #ffffff 0%, #eef4ff 100%);
    }}
    .eyebrow {{
      color: var(--accent);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 12px;
      margin-bottom: 10px;
    }}
    h1, h2, h3 {{
      margin: 0 0 12px;
    }}
    p {{
      margin: 0;
      line-height: 1.6;
    }}
    .muted {{
      color: var(--muted);
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .metric {{
      background: rgba(255, 255, 255, 0.75);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
    }}
    .metric-label {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .metric-value {{
      font-size: 26px;
      font-weight: 700;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 18px;
      margin-top: 18px;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid #e6ebf2;
      vertical-align: top;
    }}
    th {{
      font-size: 13px;
      color: var(--muted);
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    .badge.sample {{
      background: #fff7ed;
      color: #c2410c;
    }}
    .filter-form {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: end;
      margin-top: 12px;
    }}
    label {{
      font-size: 13px;
      color: var(--muted);
      display: block;
      margin-bottom: 6px;
    }}
    input {{
      min-width: 220px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 14px;
    }}
    button, .link-button {{
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
    }}
    button {{
      background: var(--accent);
      color: #ffffff;
    }}
    .link-button {{
      background: #eef2f7;
      color: var(--text);
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    li {{
      margin-bottom: 8px;
    }}
    .system-note {{
      margin-top: 18px;
      background: #f8fafc;
      border-left: 4px solid #f59e0b;
      padding: 14px 16px;
      border-radius: 12px;
    }}
    @media (max-width: 900px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="hero-card">
        <div class="eyebrow">Teacher Results Center</div>
        <h1>Classroom Interaction Results</h1>
        <p class="muted">This page is the cloud-side teacher entry for classroom interaction analysis. It focuses on readable summaries first, while MP4 upload and video archive capabilities stay as future supporting views.</p>
        <div class="metrics">
          <div class="metric">
            <span class="metric-label">Latest Classroom</span>
            <div class="metric-value">{html.escape(_stringify_value(latest_summary.get("classroom_id")))}</div>
          </div>
          <div class="metric">
            <span class="metric-label">Source Host</span>
            <div class="metric-value">{html.escape(_stringify_value(latest_summary.get("source_host")))}</div>
          </div>
          <div class="metric">
            <span class="metric-label">Generated At</span>
            <div class="metric-value">{html.escape(_format_datetime(latest_summary.get("generated_at")))}</div>
          </div>
          <div class="metric">
            <span class="metric-label">Total Events</span>
            <div class="metric-value">{html.escape(_format_metric_value(latest_summary.get("total_events")))}</div>
          </div>
          <div class="metric">
            <span class="metric-label">Participation</span>
            <div class="metric-value">{html.escape(_format_participation(latest_summary))}</div>
          </div>
        </div>
      </div>
    </section>

    <div class="layout">
      <section class="card">
        <h2>Recent Classroom Results</h2>
        <p class="muted">Results are listed in reverse chronological order. Current filter and history lookup work on file-based JSON storage.</p>
        <form class="filter-form" method="get" action="/dashboard">
          <div>
            <label for="classroom_id">Filter by classroom_id</label>
            <input id="classroom_id" name="classroom_id" value="{filter_value}" placeholder="classroom_101" />
          </div>
          <div>
            <button type="submit">Apply Filter</button>
          </div>
          <div>
            <a class="link-button" href="/dashboard">Clear Filter</a>
          </div>
        </form>
        <div class="table-wrap" style="margin-top: 18px;">
          <table>
            <thead>
              <tr>
                <th>Window</th>
                <th>Classroom</th>
                <th>Time Range</th>
                <th>Total Events</th>
                <th>Participation</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {recent_rows}
            </tbody>
          </table>
        </div>
      </section>

      <div style="display: grid; gap: 18px;">
        <section class="card">
          <h2>Latest Time Window</h2>
          <ul>
            <li><strong>Window ID:</strong> {html.escape(_stringify_value(latest_summary.get("window_id")))}</li>
            <li><strong>Started:</strong> {html.escape(_format_datetime(latest_summary.get("started_at")))}</li>
            <li><strong>Ended:</strong> {html.escape(_format_datetime(latest_summary.get("ended_at")))}</li>
            <li><strong>Generated:</strong> {html.escape(_format_datetime(latest_summary.get("generated_at")))}</li>
            <li><strong>Source Path:</strong> {html.escape(_stringify_value(latest_summary.get("source_path")))}</li>
          </ul>
        </section>

        <section class="card">
          <h2>Region / Heat Summary</h2>
          <p class="muted" style="margin-bottom: 12px;">Teachers can quickly see which seating regions showed stronger activity.</p>
          <ul>{heat_items}</ul>
        </section>

        <section class="card">
          <h2>Latest Interaction Breakdown</h2>
          <ul>{latest_counts_items}</ul>
        </section>
      </div>
    </div>

    <section class="system-note">
      <strong>System Note.</strong>
      {html.escape(result_source_note)}
      MP4 upload, video browsing, and video archive views remain preserved capabilities and will join the unified teacher entry as supporting modules in a later round.
    </section>
  </div>
</body>
</html>"""


def _recent_result_row(result: dict[str, Any]) -> str:
    summary = result.get("summary") or {}
    source_kind = result.get("source_kind") or "unknown"
    badge_class = "badge sample" if source_kind == "sample" else "badge"
    time_range = f"{_format_datetime(summary.get('started_at'))} -> {_format_datetime(summary.get('ended_at'))}"
    return (
        "<tr>"
        f"<td>{html.escape(_stringify_value(summary.get('window_id')))}</td>"
        f"<td>{html.escape(_stringify_value(summary.get('classroom_id')))}</td>"
        f"<td>{html.escape(time_range)}</td>"
        f"<td>{html.escape(_format_metric_value(summary.get('total_events')))}</td>"
        f"<td>{html.escape(_format_participation(summary))}</td>"
        f"<td><span class=\"{badge_class}\">{html.escape(_stringify_value(source_kind))}</span></td>"
        "</tr>"
    )


def _result_summary(payload: dict[str, Any]) -> dict[str, Any]:
    interaction_counts = payload.get("interaction_counts") or {}
    meta = payload.get("meta") or {}
    participants = _numeric_value(interaction_counts.get("participants"))
    if participants is None:
        participants = _numeric_value(interaction_counts.get("active_students"))

    total_students = _numeric_value(interaction_counts.get("total_students"))
    if total_students is None:
        total_students = _numeric_value(meta.get("total_students"))

    return {
        "window_id": payload.get("window_id"),
        "classroom_id": payload.get("classroom_id") or meta.get("classroom_name"),
        "source_host": payload.get("source_host"),
        "started_at": payload.get("started_at"),
        "ended_at": payload.get("ended_at"),
        "generated_at": payload.get("generated_at"),
        "interaction_counts": interaction_counts,
        "grid_stats": payload.get("grid_stats") or {},
        "total_events": _derive_total_interactions(interaction_counts),
        "participants": participants,
        "total_students": total_students,
        "participation_rate": _derive_participation_rate(interaction_counts, meta),
    }


def _render_heat_items(grid_stats: Any) -> str:
    if isinstance(grid_stats, dict) and grid_stats:
        ranked_items = []
        for key, value in grid_stats.items():
            total = _sum_numeric_values(value)
            ranked_items.append((key, total, value))
        ranked_items.sort(key=lambda item: item[1], reverse=True)
        return "".join(
            f"<li><strong>{html.escape(str(key))}</strong>: {_format_heat_description(total, value)}</li>"
            for key, total, value in ranked_items
        )
    if isinstance(grid_stats, list) and grid_stats:
        return "".join(f"<li>{html.escape(_stringify_value(item))}</li>" for item in grid_stats)
    return "<li>No grid statistics are available yet.</li>"


def _render_interaction_items(interaction_counts: dict[str, Any]) -> str:
    items = [
        f"<li><strong>{html.escape(str(key))}</strong>: {html.escape(_stringify_value(value))}</li>"
        for key, value in interaction_counts.items()
    ]
    return "".join(items) or "<li>No interaction counts are available yet.</li>"


def _format_heat_description(total: float, value: Any) -> str:
    intensity = "higher activity" if total > 0 else "no recorded activity"
    detail = _stringify_value(value)
    return f"{html.escape(_format_metric_value(total))} events, {intensity} ({html.escape(detail)})"


def _sum_numeric_values(value: Any) -> float:
    if isinstance(value, dict):
        return sum(_sum_numeric_values(item) for item in value.values())
    if isinstance(value, list):
        return sum(_sum_numeric_values(item) for item in value)
    numeric_value = _numeric_value(value)
    return numeric_value or 0.0


def _format_datetime(value: Any) -> str:
    if value in (None, ""):
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _numeric_value(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _derive_total_interactions(interaction_counts: dict[str, Any]) -> Optional[float]:
    explicit_total = _numeric_value(interaction_counts.get("total_events"))
    if explicit_total is not None:
        return explicit_total

    excluded_keys = {"participants", "active_students", "total_students", "participation_rate"}
    total = 0.0
    found = False
    for key, value in interaction_counts.items():
        if key in excluded_keys:
            continue
        numeric_value = _numeric_value(value)
        if numeric_value is None:
            continue
        total += numeric_value
        found = True
    return total if found else None


def _derive_participation_rate(interaction_counts: dict[str, Any], meta: dict[str, Any]) -> Optional[float]:
    explicit_rate = _numeric_value(interaction_counts.get("participation_rate"))
    if explicit_rate is None:
        explicit_rate = _numeric_value(meta.get("participation_rate"))
    if explicit_rate is not None:
        return explicit_rate

    participant_count = _numeric_value(interaction_counts.get("participants"))
    if participant_count is None:
        participant_count = _numeric_value(interaction_counts.get("active_students"))

    total_students = _numeric_value(interaction_counts.get("total_students"))
    if total_students is None:
        total_students = _numeric_value(meta.get("total_students"))

    if participant_count is not None and total_students not in (None, 0):
        return (participant_count / total_students) * 100
    return None


def _format_participation(summary: dict[str, Any]) -> str:
    participation_rate = summary.get("participation_rate")
    participants = summary.get("participants")
    total_students = summary.get("total_students")
    if isinstance(participation_rate, (int, float)):
        if isinstance(participants, (int, float)) and isinstance(total_students, (int, float)) and total_students:
            return f"{participation_rate:.1f}% ({int(participants)}/{int(total_students)})"
        return f"{participation_rate:.1f}%"
    if isinstance(participants, (int, float)) and isinstance(total_students, (int, float)) and total_students:
        return f"{(participants / total_students) * 100:.1f}% ({int(participants)}/{int(total_students)})"
    if isinstance(participants, (int, float)):
        return f"{int(participants)} students"
    return "N/A"


def _format_metric_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(round(float(value), 2))
    return str(value)


def _stringify_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = [f"{key}: {_stringify_value(inner_value)}" for key, inner_value in value.items()]
        return ", ".join(parts) if parts else "empty"
    if isinstance(value, list):
        return ", ".join(_stringify_value(item) for item in value) if value else "empty"
    if value in (None, ""):
        return "N/A"
    return str(value)
