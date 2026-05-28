from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SOURCE_NAME = "local_real_classroom_sample"
SOURCE_TYPE = "own_real_classroom_session"
DATA_MODE = "local_real_classroom_session"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 3.4e real classroom validation report.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    reports_dir = sample_root / "reports"
    manifest_csv = reports_dir / "real_classroom_sample_manifest.csv"
    status_csv = reports_dir / "real_classroom_analysis_status.csv"
    report_md = reports_dir / "real_classroom_validation_report.md"
    manifest_rows = _read_rows(manifest_csv) if manifest_csv.exists() else []
    status_rows = _read_rows(status_csv) if status_csv.exists() else []
    manifest = manifest_rows[0] if manifest_rows else {}
    status = status_rows[0] if status_rows else {}
    result_payload = _read_json(Path(str(status.get("result_json") or ""))) if status.get("result_json") else {}

    reports_dir.mkdir(parents=True, exist_ok=True)
    report_md.write_text(_build_report(manifest=manifest, status=status, result_payload=result_payload), encoding="utf-8")
    print(f"PHASE34_REAL_CLASSROOM_REPORT={report_md}")
    print(f"PHASE34_REAL_CLASSROOM_REPORT_PRESENT={_bool_text(report_md.exists())}")
    return 0 if report_md.exists() else 1


def _build_report(*, manifest: dict[str, str], status: dict[str, str], result_payload: dict[str, Any]) -> str:
    video_present = bool(manifest.get("source_video_path") and Path(str(manifest.get("source_video_path"))).exists())
    analysis_success = status.get("analysis_status") == "success"
    summary = result_payload.get("summary") if isinstance(result_payload.get("summary"), dict) else {}
    students = result_payload.get("students") if isinstance(result_payload.get("students"), dict) else {}
    teacher = result_payload.get("teacher") if isinstance(result_payload.get("teacher"), dict) else {}
    timeline = result_payload.get("timeline") if isinstance(result_payload.get("timeline"), dict) else {}
    activity_curve = timeline.get("activity_curve") if isinstance(timeline.get("activity_curve"), list) else []
    hand_raise_count = _safe_int(students.get("hand_raise_event_count"))
    active_window_count = sum(1 for value in activity_curve if _safe_float(value) > 0)
    standing_detected = active_window_count > 0
    question_events = teacher.get("question_events") if isinstance(teacher.get("question_events"), list) else []

    if not video_present:
        return f"""# Phase 3.4e 实际完整课堂分析样本

## 当前状态

- 视频来源：{DATA_MODE}
- 视频文件：未找到
- 分析状态：待分析

请将 1 个实际完整课堂视频放到 `C:\\Users\\lyy\\Desktop\\gradu\\real_classroom_samples` 后重新运行：

```powershell
python scripts\\phase3_4_prepare_real_classroom_sample.py
python scripts\\phase3_4_analyze_real_classroom_sample.py
python scripts\\phase3_4_generate_real_classroom_report.py
```
"""

    return f"""# Phase 3.4e 实际完整课堂分析样本

## 视频来源

- `source_name`: {SOURCE_NAME}
- `source_type`: {SOURCE_TYPE}
- `data_mode`: {DATA_MODE}
- `is_demo`: false
- `is_own_capture`: true
- 是否为树莓派采集：{manifest.get("raspberry_pi_capture") or "unknown"}（{manifest.get("raspberry_pi_capture_note") or "unknown"}）
- 源视频：`{manifest.get("source_video_path") or ""}`

## 样本信息

- sample_id: `{manifest.get("sample_id") or ""}`
- classroom_id: `{manifest.get("classroom_id") or ""}`
- session_id: `{manifest.get("session_id") or ""}`
- 视频时长: {status.get("duration_seconds") or manifest.get("duration_seconds") or "0"} 秒
- 分析是否成功: {_bool_text(analysis_success)}

## 主要课堂行为统计

- feedback_score: {summary.get("feedback_score", status.get("feedback_score", ""))}
- attention_score: {summary.get("attention_score", "")}
- response_score: {summary.get("response_score", "")}
- teacher_question_count: {summary.get("teacher_question_count", len(question_events))}
- hand_raise_event_count: {hand_raise_count}
- active_window_count: {active_window_count}

## 站立、举手、互动行为识别摘要

- 举手识别：{"检测到举手信号" if hand_raise_count > 0 else "未检测到明显举手信号"}
- 站立/活动识别：{"检测到活动/站立相关窗口，当前聚合结果以 activity_curve 推断" if standing_detected else "未检测到明显站立/活动窗口"}
- 互动行为：教师提问事件 {len(question_events)} 个，当前样本主要用于验证完整课堂级分析链路可跑通。

## 与 SAV-50 的关系

SAV-50 是外部真实课堂切片验证集，用于对 `raise_hand` / `stand` 等核心行为做切片级可信度验证。本视频是实际完整课堂样本，用于说明本地端可以处理完整课堂视频并生成课堂级反馈。两者互补，不互相替代。

## 当前边界

- 不宣称完整识别 SAV 15 类动作。
- 不宣称大规模真实部署。
- 当前完整课堂样本为 1 个，仅用于 Phase 3.4 最终数据形态收口。
- 若需要云端展示，应作为后续阶段单独设计；本阶段未上传云端。
"""


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


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
