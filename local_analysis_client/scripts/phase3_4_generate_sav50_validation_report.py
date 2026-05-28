from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")

SUMMARY_FIELDS = ("metric", "expected_count", "matched_count", "match_rate", "notes")
EXAMPLE_FIELDS = (
    "clip_id",
    "final_phase34_category_cn",
    "sav_stand_count",
    "sav_raise_hand_count",
    "local_detected_standing",
    "local_detected_raise_hand",
    "stand_matched",
    "raise_hand_matched",
    "example_type",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 3.4 SAV-50 local validation report materials.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--review-csv", type=Path, default=None)
    parser.add_argument("--analysis-status-csv", type=Path, default=None)
    parser.add_argument("--comparison-csv", type=Path, default=None)
    parser.add_argument("--comparison-summary-json", type=Path, default=None)
    parser.add_argument("--report-md", type=Path, default=None)
    parser.add_argument("--detection-summary-csv", type=Path, default=None)
    parser.add_argument("--hit-miss-examples-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    review_csv = args.review_csv.resolve() if args.review_csv else reports_dir / "final_sav50_manual_review_results.csv"
    analysis_status_csv = args.analysis_status_csv.resolve() if args.analysis_status_csv else reports_dir / "sav50_local_analysis_status.csv"
    comparison_csv = args.comparison_csv.resolve() if args.comparison_csv else reports_dir / "sav50_local_comparison.csv"
    comparison_summary_json = (
        args.comparison_summary_json.resolve()
        if args.comparison_summary_json
        else reports_dir / "sav50_local_comparison_summary.json"
    )
    report_md = args.report_md.resolve() if args.report_md else reports_dir / "sav50_validation_report.md"
    detection_summary_csv = (
        args.detection_summary_csv.resolve()
        if args.detection_summary_csv
        else reports_dir / "sav50_detection_summary.csv"
    )
    hit_miss_examples_csv = (
        args.hit_miss_examples_csv.resolve()
        if args.hit_miss_examples_csv
        else reports_dir / "sav50_hit_miss_examples.csv"
    )

    review_rows = _read_rows(review_csv) if review_csv.exists() else []
    analysis_rows = _read_rows(analysis_status_csv) if analysis_status_csv.exists() else []
    comparison_rows = _read_rows(comparison_csv) if comparison_csv.exists() else []
    comparison_summary = _read_json(comparison_summary_json) if comparison_summary_json.exists() else {}

    dataset_counts = Counter(row.get("final_phase34_category") for row in review_rows)
    analysis_success = sum(1 for row in analysis_rows if row.get("analysis_status") == "success")
    analysis_failed = sum(1 for row in analysis_rows if row.get("analysis_status") == "failed")
    metrics = _resolve_metrics(comparison_summary, analysis_success=analysis_success, analysis_total=len(analysis_rows))
    detection_summary_rows = _build_detection_summary_rows(metrics, analysis_success=analysis_success, analysis_failed=analysis_failed)
    hit_miss_rows = _build_hit_miss_examples(comparison_rows)

    reports_dir.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        _build_report_markdown(
            dataset_counts=dataset_counts,
            package_count=len(review_rows),
            analysis_success=analysis_success,
            analysis_failed=analysis_failed,
            metrics=metrics,
        ),
        encoding="utf-8",
    )
    _write_rows(detection_summary_csv, detection_summary_rows, SUMMARY_FIELDS)
    _write_rows(hit_miss_examples_csv, hit_miss_rows, EXAMPLE_FIELDS)

    ok = report_md.exists() and detection_summary_csv.exists() and hit_miss_examples_csv.exists()
    print(f"PHASE34_SAV50_REPORT_MD={report_md}")
    print(f"PHASE34_SAV50_DETECTION_SUMMARY_CSV={detection_summary_csv}")
    print(f"PHASE34_SAV50_HIT_MISS_EXAMPLES_CSV={hit_miss_examples_csv}")
    print(f"PHASE34_SAV50_REPORT_GENERATED={_bool_text(ok)}")
    print(f"PHASE34_SAV50_RAISE_HAND_MATCH_RATE={metrics['raise_hand_match_rate']}")
    print(f"PHASE34_SAV50_STAND_MATCH_RATE={metrics['stand_match_rate']}")
    return 0 if ok else 1


def _resolve_metrics(summary: dict[str, Any], *, analysis_success: int, analysis_total: int) -> dict[str, Any]:
    raise_expected = int(summary.get("raise_hand_expected_count") or 0)
    raise_matched = int(summary.get("raise_hand_matched_count") or 0)
    stand_expected = int(summary.get("stand_expected_count") or 0)
    stand_matched = int(summary.get("stand_matched_count") or 0)
    return {
        "analysis_total": analysis_total,
        "analysis_success": analysis_success,
        "analysis_success_rate": _rate(analysis_success, analysis_total),
        "raise_hand_expected": raise_expected,
        "raise_hand_matched": raise_matched,
        "raise_hand_match_rate": _rate(raise_matched, raise_expected),
        "stand_expected": stand_expected,
        "stand_matched": stand_matched,
        "stand_match_rate": _rate(stand_matched, stand_expected),
    }


def _build_detection_summary_rows(metrics: dict[str, Any], *, analysis_success: int, analysis_failed: int) -> list[dict[str, str]]:
    return [
        {
            "metric": "raise_hand",
            "expected_count": str(metrics["raise_hand_expected"]),
            "matched_count": str(metrics["raise_hand_matched"]),
            "match_rate": metrics["raise_hand_match_rate"],
            "notes": "SAV 官方标签/人工复核期望与本地端 raise_hand 识别结果对照。",
        },
        {
            "metric": "stand",
            "expected_count": str(metrics["stand_expected"]),
            "matched_count": str(metrics["stand_matched"]),
            "match_rate": metrics["stand_match_rate"],
            "notes": "stand 对照部分存在基于当前聚合结果 activity_curve 的推断，不是直接 per-person 站立检测字段。",
        },
        {
            "metric": "analysis_success",
            "expected_count": str(analysis_success + analysis_failed),
            "matched_count": str(analysis_success),
            "match_rate": _rate(analysis_success, analysis_success + analysis_failed),
            "notes": "本地端 analyze_delivery_package 对 SAV-50 package 的批量分析成功情况。",
        },
    ]


def _build_hit_miss_examples(comparison_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in comparison_rows:
        for example_type in _example_types_for_row(row):
            if len(grouped[example_type]) < 10:
                grouped[example_type].append(_example_row(row, example_type))

    ordered_types = ("both_hit", "both_miss", "raise_hand_hit", "raise_hand_miss", "stand_hit", "stand_miss")
    output_rows: list[dict[str, str]] = []
    for example_type in ordered_types:
        output_rows.extend(grouped.get(example_type, []))
    return output_rows


def _example_types_for_row(row: dict[str, str]) -> list[str]:
    stand_expected = row.get("stand_expected") == "true"
    raise_expected = row.get("raise_hand_expected") == "true"
    stand_hit = stand_expected and row.get("stand_matched") == "true"
    stand_miss = stand_expected and row.get("stand_matched") == "false"
    raise_hit = raise_expected and row.get("raise_hand_matched") == "true"
    raise_miss = raise_expected and row.get("raise_hand_matched") == "false"

    types: list[str] = []
    if stand_hit and raise_hit:
        types.append("both_hit")
    if stand_miss and raise_miss:
        types.append("both_miss")
    if raise_hit:
        types.append("raise_hand_hit")
    if raise_miss:
        types.append("raise_hand_miss")
    if stand_hit:
        types.append("stand_hit")
    if stand_miss:
        types.append("stand_miss")
    return types


def _example_row(row: dict[str, str], example_type: str) -> dict[str, str]:
    return {
        "clip_id": str(row.get("clip_id") or ""),
        "final_phase34_category_cn": str(row.get("final_phase34_category_cn") or ""),
        "sav_stand_count": str(row.get("sav_stand_count") or ""),
        "sav_raise_hand_count": str(row.get("sav_raise_hand_count") or ""),
        "local_detected_standing": str(row.get("local_detected_standing") or ""),
        "local_detected_raise_hand": str(row.get("local_detected_raise_hand") or ""),
        "stand_matched": str(row.get("stand_matched") or ""),
        "raise_hand_matched": str(row.get("raise_hand_matched") or ""),
        "example_type": example_type,
        "notes": str(row.get("notes") or ""),
    }


def _build_report_markdown(
    *,
    dataset_counts: Counter[str],
    package_count: int,
    analysis_success: int,
    analysis_failed: int,
    metrics: dict[str, Any],
) -> str:
    return f"""# Phase 3.4 SAV-50 外部真实课堂切片验证

## 数据来源

- `source_name`: SAV
- `source_type`: public_dataset
- `data_mode`: external_real_clip
- `is_demo`: false
- `is_own_capture`: false

## 数据集构成

- total = {package_count}
- question_interaction = {dataset_counts.get("question_interaction", 0)}
- classroom_routine_standing = {dataset_counts.get("classroom_routine_standing", 0)}
- classroom_routine_bending = {dataset_counts.get("classroom_routine_bending", 0)}

## 处理链路

SAV 官方标注 -> 人工复核分类 -> 本地端批量分析 -> 对照表。

## 本地端分析结果

- package = {package_count}
- analysis_success = {analysis_success}
- analysis_failed = {analysis_failed}

## 对照结果

| 指标 | expected | matched | match_rate |
| --- | ---: | ---: | ---: |
| raise_hand | {metrics["raise_hand_expected"]} | {metrics["raise_hand_matched"]} | {metrics["raise_hand_match_rate"]} |
| stand | {metrics["stand_expected"]} | {metrics["stand_matched"]} | {metrics["stand_match_rate"]} |

## 结论

当前本地端在外部真实课堂切片上对举手、站立等核心行为具备一定识别能力。结果体现的是课堂级行为分析可信度，不等同于 SAV 级别的逐人多动作识别。

## 风险与边界

- 不宣称完整识别 SAV 15 类动作。
- SAV 不是树莓派自采数据。
- bend 标签经人工复核多为课堂流程性弯腰，不作为注意力下降结论。
- stand 对照部分存在基于当前聚合结果的推断，不是直接 per-person 站立检测字段。

## 后续改进

- 增强 person-level 行为证据。
- 扩展低头、转身、交谈、回答问题等动作识别。
- 引入更多自采课堂样本。
- 云端可后续增加实验验证结果展示。
"""


def _rate(matched: int, expected: int) -> str:
    if expected <= 0:
        return "0.0%"
    return f"{(matched / expected) * 100:.1f}%"


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, str]], fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
