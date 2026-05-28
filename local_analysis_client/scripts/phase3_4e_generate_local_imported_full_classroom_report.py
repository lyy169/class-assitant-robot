from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SAMPLE_ID = "local_imported_sav_full_classroom_20200908_17"
SOURCE_VIDEO_ID = "20200908_17"

SUMMARY_FIELDS = ("metric", "value", "notes")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate report for Phase 3.4e local imported SAV full-classroom video.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    reports_dir = sample_root / "reports"
    manifest_csv = reports_dir / "local_imported_full_classroom_manifest.csv"
    status_csv = reports_dir / "local_imported_full_classroom_analysis_status.csv"
    summary_csv = reports_dir / "local_imported_full_classroom_summary.csv"
    report_md = reports_dir / "local_imported_full_classroom_validation_report.md"
    manifest = _read_first_row(manifest_csv)
    status = _read_first_row(status_csv)
    result_payload = _read_json(Path(str(status.get("result_json") or ""))) if status.get("result_json") else {}
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = _build_summary_rows(manifest=manifest, status=status, result_payload=result_payload)
    _write_rows(summary_csv, summary_rows)
    report_md.write_text(_build_report(manifest=manifest, status=status, result_payload=result_payload), encoding="utf-8")

    print(f"PHASE34E_LOCAL_IMPORTED_SUMMARY_CSV={summary_csv}")
    print(f"PHASE34E_LOCAL_IMPORTED_REPORT={report_md}")
    print(f"PHASE34E_LOCAL_IMPORTED_REPORT_PRESENT={_bool_text(report_md.exists())}")
    return 0 if report_md.exists() and summary_csv.exists() else 1


def _build_summary_rows(*, manifest: dict[str, str], status: dict[str, str], result_payload: dict[str, Any]) -> list[dict[str, str]]:
    summary = result_payload.get("summary") if isinstance(result_payload.get("summary"), dict) else {}
    return [
        {"metric": "source_video_id", "value": SOURCE_VIDEO_ID, "notes": "SAV public dataset source video id."},
        {"metric": "video_path", "value": manifest.get("video_path", ""), "notes": "Local imported full-classroom video path."},
        {"metric": "duration_seconds", "value": status.get("duration_seconds") or manifest.get("duration_seconds", ""), "notes": "Detected by local tools when available."},
        {"metric": "video_size_bytes", "value": manifest.get("video_size_bytes", ""), "notes": "Local full video file size."},
        {"metric": "download_status", "value": manifest.get("download_status", ""), "notes": "Downloaded by yt-dlp or reused if existing."},
        {"metric": "analysis_status", "value": status.get("analysis_status", ""), "notes": "Local analyzer result."},
        {"metric": "feedback_score", "value": str(summary.get("feedback_score", status.get("feedback_score", ""))), "notes": "Existing local classroom feedback summary."},
        {"metric": "hand_raise_event_count", "value": status.get("hand_raise_event_count", ""), "notes": "Extracted from local result students.hand_raise_event_count."},
        {"metric": "active_window_count", "value": status.get("active_window_count", ""), "notes": "Inferred from timeline.activity_curve > 0."},
    ]


def _build_report(*, manifest: dict[str, str], status: dict[str, str], result_payload: dict[str, Any]) -> str:
    video_path = Path(str(manifest.get("video_path") or ""))
    video_present = video_path.exists()
    analysis_success = status.get("analysis_status") == "success"
    summary = result_payload.get("summary") if isinstance(result_payload.get("summary"), dict) else {}
    students = result_payload.get("students") if isinstance(result_payload.get("students"), dict) else {}
    teacher = result_payload.get("teacher") if isinstance(result_payload.get("teacher"), dict) else {}
    timeline = result_payload.get("timeline") if isinstance(result_payload.get("timeline"), dict) else {}
    activity_curve = timeline.get("activity_curve") if isinstance(timeline.get("activity_curve"), list) else []
    hand_raise_count = _safe_int(students.get("hand_raise_event_count"))
    active_window_count = sum(1 for value in activity_curve if _safe_float(value) > 0)
    question_events = teacher.get("question_events") if isinstance(teacher.get("question_events"), list) else []

    return f"""# Phase 3.4e 本地导入完整课堂视频分析报告

## 1. 样本来源

- SAV 公开数据集完整课堂视频。
- 本地导入视频。
- 由本地分析端处理。
- 不是树莓派采集：`is_pi_capture=false`。
- 不是项目自采集数据：`is_own_capture=false`。
- `source_dataset=SAV`
- `source_type=local_imported_video`
- `sample_type=external_full_classroom_video`
- `is_local_processed=true`

## 2. 样本价值

- SAV-50 用于外部真实课堂切片验证。
- 本完整视频用于验证本地端能否处理完整课堂视频流程。
- 两者互补：切片验证关注核心动作可信度，完整视频验证端到端本地分析流程。

## 3. 视频信息

- `source_video_id`: {SOURCE_VIDEO_ID}
- 本地视频路径：`{manifest.get("video_path", "")}`
- 视频时长：{status.get("duration_seconds") or manifest.get("duration_seconds") or "unknown"} 秒
- 文件大小：{manifest.get("video_size_bytes") or (video_path.stat().st_size if video_present else 0)} bytes
- 是否成功下载：{_bool_text(video_present)}
- 下载状态：{manifest.get("download_status", "")}
- 是否成功分析：{_bool_text(analysis_success)}

## 4. 本地分析结果摘要

- 分析状态：{status.get("analysis_status", "")}
- 输出结果目录：`{Path(str(status.get("result_json") or "")).parent if status.get("result_json") else ""}`
- feedback_score：{summary.get("feedback_score", status.get("feedback_score", ""))}
- attention_score：{summary.get("attention_score", status.get("attention_score", ""))}
- response_score：{summary.get("response_score", status.get("response_score", ""))}
- teacher_question_count：{summary.get("teacher_question_count", status.get("teacher_question_count", ""))}
- hand_raise_event_count：{hand_raise_count}
- active_window_count：{active_window_count}

站立/举手/互动相关字段摘要：

- 举手信号来自 `students.hand_raise_event_count`。
- 互动信号结合 `teacher.question_events`、`summary.response_score` 和 `timeline.activity_curve`。
- 当前聚合结果没有直接 per-person 站立字段；站立/活动摘要从现有结果字段中提取或推断。
- 教师提问事件数：{len(question_events)}。

## 5. 已知关键事件

- 16:27.5-16:30.5 附近存在大量举手和少量站立。
- 该事件来自人工观察，不是自动标注。

## 6. 边界说明

- 不宣称完整识别 SAV 15 类动作。
- 不宣称这是树莓派采集样本。
- 不宣称这是项目自采集课堂数据。
- 不作为严格逐帧准确率评估。
- 主要用于完整课堂流程验证。

## 7. 与项目最终形态的关系

当前 Phase 3.4 数据闭环为：

- 50 个 SAV 外部真实课堂切片验证。
- 1 个 SAV 外部真实完整课堂视频的本地导入分析。
- 树莓派端另作为语音交互式采集终端能力说明。
"""


def _read_first_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return rows[0] if rows else {}


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in SUMMARY_FIELDS})


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(str(value or "0"))
    except ValueError:
        return 0.0


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
