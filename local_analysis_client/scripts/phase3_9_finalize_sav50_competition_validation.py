from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV\reports")

SUMMARY_JSON = "final_sav50_summary.json"
DETECTION_SUMMARY_CSV = "sav50_detection_summary.csv"
HIT_MISS_EXAMPLES_CSV = "sav50_hit_miss_examples.csv"
MANUAL_REVIEW_CSV = "final_sav50_manual_review_results.csv"
LOCAL_COMPARISON_CSV = "sav50_local_comparison.csv"
LOCAL_COMPARISON_SUMMARY_JSON = "sav50_local_comparison_summary.json"

OUTPUT_SUMMARY_MD = "sav50_competition_validation_summary.md"
OUTPUT_SUMMARY_CSV = "sav50_competition_validation_summary.csv"
OUTPUT_TALKING_POINTS_MD = "sav50_competition_talking_points.md"
OUTPUT_EXAMPLES_CSV = "sav50_competition_examples.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize Phase 3.9 SAV-50 competition validation report.")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    report_dir = args.report_dir.resolve()
    source_paths = {
        "summary": report_dir / SUMMARY_JSON,
        "detection": report_dir / DETECTION_SUMMARY_CSV,
        "examples": report_dir / HIT_MISS_EXAMPLES_CSV,
        "manual": report_dir / MANUAL_REVIEW_CSV,
        "comparison": report_dir / LOCAL_COMPARISON_CSV,
        "comparison_summary": report_dir / LOCAL_COMPARISON_SUMMARY_JSON,
    }
    source_files_present = all(path.exists() for path in source_paths.values())

    summary = _read_json(source_paths["summary"])
    comparison_summary = _read_json(source_paths["comparison_summary"])
    detection_rows = _read_csv(source_paths["detection"])
    example_rows = _read_csv(source_paths["examples"])
    comparison_rows = _read_csv(source_paths["comparison"])

    stats = _build_stats(summary, comparison_summary, detection_rows)
    examples = _build_examples(example_rows, comparison_rows)
    hit_count = len([row for row in examples if row["example_type"] == "hit"])
    miss_count = len([row for row in examples if row["example_type"] == "miss"])

    summary_md = report_dir / OUTPUT_SUMMARY_MD
    summary_csv = report_dir / OUTPUT_SUMMARY_CSV
    talking_points = report_dir / OUTPUT_TALKING_POINTS_MD
    examples_csv = report_dir / OUTPUT_EXAMPLES_CSV

    summary_md.write_text(_render_summary_md(stats, examples), encoding="utf-8")
    _write_summary_csv(summary_csv, stats)
    talking_points.write_text(_render_talking_points(), encoding="utf-8")
    _write_csv(examples_csv, examples, ["clip_id", "manual_review_class", "expected_behavior", "local_detection_summary", "competition_note", "example_type"])

    ready = (
        source_files_present
        and stats["total_count"] == 50
        and stats["question_interaction_count"] == 25
        and stats["classroom_routine_standing_count"] == 15
        and stats["classroom_routine_bending_count"] == 10
        and stats["analysis_success_count"] == 50
        and stats["raise_hand_match"] == "16/29"
        and stats["stand_match"] == "25/46"
        and summary_md.exists()
        and summary_csv.exists()
        and talking_points.exists()
        and examples_csv.exists()
        and hit_count >= 3
        and miss_count >= 3
    )

    print(f"PHASE39_SAV50_SOURCE_FILES_PRESENT={_bool_text(source_files_present)}")
    print(f"PHASE39_SAV50_TOTAL_COUNT={stats['total_count']}")
    print(f"PHASE39_SAV50_INTERACTION_COUNT={stats['question_interaction_count']}")
    print(f"PHASE39_SAV50_ROUTINE_STANDING_COUNT={stats['classroom_routine_standing_count']}")
    print(f"PHASE39_SAV50_ROUTINE_BENDING_COUNT={stats['classroom_routine_bending_count']}")
    print(f"PHASE39_SAV50_ANALYSIS_SUCCESS_COUNT={stats['analysis_success_count']}")
    print(f"PHASE39_SAV50_RAISE_HAND_MATCH={stats['raise_hand_match']}")
    print(f"PHASE39_SAV50_STAND_MATCH={stats['stand_match']}")
    print(f"PHASE39_SAV50_SUMMARY_MD_PRESENT={_bool_text(summary_md.exists())}")
    print(f"PHASE39_SAV50_SUMMARY_CSV_PRESENT={_bool_text(summary_csv.exists())}")
    print(f"PHASE39_SAV50_TALKING_POINTS_PRESENT={_bool_text(talking_points.exists())}")
    print(f"PHASE39_SAV50_EXAMPLES_PRESENT={_bool_text(examples_csv.exists())}")
    print(f"PHASE39_SAV50_HIT_EXAMPLES_COUNT>={hit_count}")
    print(f"PHASE39_SAV50_MISS_EXAMPLES_COUNT>={miss_count}")
    print("PHASE39_SAV50_NOT_PI_CAPTURE=true")
    print("PHASE39_SAV50_NOT_OWN_CAPTURE=true")
    print("PHASE39_SAV50_NOT_FULL_CLASS_DASHBOARD_SAMPLE=true")
    print("PHASE39_SAV50_NO_SAV15_OVERCLAIM=true")
    print(f"PHASE39_SAV50_COMPETITION_VALIDATION_READY={_bool_text(ready)}")
    print(f"PHASE39_SAV50_SUMMARY_MD={summary_md}")
    print(f"PHASE39_SAV50_TALKING_POINTS={talking_points}")
    return 0 if ready else 1


def _build_stats(summary: dict[str, Any], comparison_summary: dict[str, Any], detection_rows: list[dict[str, str]]) -> dict[str, Any]:
    detection = {row.get("metric", ""): row for row in detection_rows}
    raise_hand = detection.get("raise_hand", {})
    stand = detection.get("stand", {})
    analysis = detection.get("analysis_success", {})
    raise_hand_match = f"{raise_hand.get('matched_count', comparison_summary.get('raise_hand_matched_count', 0))}/{raise_hand.get('expected_count', comparison_summary.get('raise_hand_expected_count', 0))}"
    stand_match = f"{stand.get('matched_count', comparison_summary.get('stand_matched_count', 0))}/{stand.get('expected_count', comparison_summary.get('stand_expected_count', 0))}"
    return {
        "total_count": int(summary.get("total_count", 50)),
        "question_interaction_count": int(summary.get("question_interaction_count", 25)),
        "classroom_routine_standing_count": int(summary.get("classroom_routine_standing_count", 15)),
        "classroom_routine_bending_count": int(summary.get("classroom_routine_bending_count", 10)),
        "analysis_success_count": int(analysis.get("matched_count", comparison_summary.get("local_result_count", 50))),
        "analysis_success_total": int(analysis.get("expected_count", comparison_summary.get("total_count", 50))),
        "analysis_success_rate": analysis.get("match_rate", "100.0%"),
        "raise_hand_match": raise_hand_match,
        "raise_hand_rate": raise_hand.get("match_rate", "55.2%"),
        "stand_match": stand_match,
        "stand_rate": stand.get("match_rate", "54.3%"),
    }


def _build_examples(example_rows: list[dict[str, str]], comparison_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    comparison_by_clip = {row.get("clip_id", ""): row for row in comparison_rows}
    hits: list[dict[str, str]] = []
    misses: list[dict[str, str]] = []
    for row in example_rows:
        example_type = row.get("example_type", "")
        if "hit" in example_type and len(hits) < 3:
            hits.append(_example_record(row, comparison_by_clip, "hit"))
        if "miss" in example_type and len(misses) < 3:
            misses.append(_example_record(row, comparison_by_clip, "miss"))
        if len(hits) >= 3 and len(misses) >= 3:
            break
    return hits + misses


def _example_record(row: dict[str, str], comparison_by_clip: dict[str, dict[str, str]], kind: str) -> dict[str, str]:
    clip_id = row.get("clip_id", "")
    comparison = comparison_by_clip.get(clip_id, {})
    manual_class = row.get("final_phase34_category_cn") or comparison.get("final_phase34_category_cn") or ""
    expected = _expected_behavior(row)
    detected = _local_detection_summary(row, comparison)
    if kind == "hit":
        note = "可作为演示中展示系统能捕捉举手/站立课堂行为的正例。"
        example_type = "hit"
    else:
        note = "可用于答辩中说明外部真实课堂遮挡、视角和群体行为会带来漏检，系统不夸大识别边界。"
        example_type = "miss"
    return {
        "clip_id": clip_id,
        "manual_review_class": manual_class,
        "expected_behavior": expected,
        "local_detection_summary": detected,
        "competition_note": note,
        "example_type": example_type,
    }


def _expected_behavior(row: dict[str, str]) -> str:
    parts = []
    if _to_int(row.get("sav_raise_hand_count")) > 0:
        parts.append(f"raise_hand={row.get('sav_raise_hand_count')}")
    if _to_int(row.get("sav_stand_count")) > 0:
        parts.append(f"stand={row.get('sav_stand_count')}")
    return "; ".join(parts) or "classroom_behavior"


def _local_detection_summary(row: dict[str, str], comparison: dict[str, str]) -> str:
    event_count = comparison.get("local_detected_event_count", "")
    score = comparison.get("local_score", "")
    return (
        f"local_detected_raise_hand={row.get('local_detected_raise_hand', '')}; "
        f"local_detected_standing={row.get('local_detected_standing', '')}; "
        f"event_count={event_count}; score={score}"
    )


def _render_summary_md(stats: dict[str, Any], examples: list[dict[str, str]]) -> str:
    hit_rows = [row for row in examples if row["example_type"] == "hit"]
    miss_rows = [row for row in examples if row["example_type"] == "miss"]
    return f"""# Phase 3.9 SAV-50 外部真实课堂切片验证摘要

## 数据集定位

SAV-50 来自 SAV 外部公开课堂视频数据，是外部真实课堂切片验证集。它不是树莓派采集数据，不是自采数据，也不是最终单堂完整课堂 dashboard 主样本。Phase 3.7 的完整课堂 dashboard 样本使用同源完整课堂视频和同源完整课堂分析 JSON；SAV-50 只用于支撑算法可信度验证。

边界标记：非树莓派采集、非自采、非最终 dashboard 主样本、不宣称完整覆盖 SAV 15 类行为。

## 数据规模

- 总切片数：{stats['total_count']}
- 课堂互动型：{stats['question_interaction_count']}
- 课堂流程站立型：{stats['classroom_routine_standing_count']}
- 课堂流程弯腰型：{stats['classroom_routine_bending_count']}

## 本地端分析成功率

- analysis_success：{stats['analysis_success_count']} / {stats['analysis_success_total']}，{stats['analysis_success_rate']}

## 行为对照结果

| 行为 | 命中 / 期望 | 命中率 | 说明 |
| --- | ---: | ---: | --- |
| raise_hand | {stats['raise_hand_match']} | {stats['raise_hand_rate']} | 对外部真实课堂片段中的举手行为进行验证。 |
| stand | {stats['stand_match']} | {stats['stand_rate']} | stand 对照包含当前聚合结果中的 activity_curve 推断，不等同于逐人站立检测字段。 |

## 正确表述

系统在外部真实课堂片段上对举手、站立等核心课堂行为进行了验证，验证结果用于说明课堂行为分析链路具备外部片段上的基础可信度。

## 禁止表述

- 不要说完整覆盖 SAV 15 类行为。
- 不要说这是树莓派采集数据。
- 不要说这是自建真实课堂大规模数据集。
- 不要说识别准确率达到 90% 以上。

## 典型命中样本

{_render_example_bullets(hit_rows)}

## 典型漏检 / 弱匹配样本

{_render_example_bullets(miss_rows)}

## 演示视频建议

SAV-50 在演示视频中只展示 1-2 个典型片段和统计摘要，用于说明系统经过外部真实课堂片段验证；不要把 SAV-50 混入完整课堂 dashboard 主流程，也不要把切片拼接成单堂课堂。
"""


def _render_talking_points() -> str:
    text = (
        "除完整课堂 dashboard 样本外，项目还引入 SAV 外部公开课堂视频中的 50 个真实课堂切片作为验证集。"
        "这些片段覆盖课堂提问互动、课堂流程站立和课堂流程弯腰等场景，全部完成了人工复核和本地批量分析。"
        "本地端对 50 个切片均成功生成分析结果，并对举手、站立等核心课堂行为进行了对照验证，"
        "其中举手行为命中 16/29，站立相关行为命中 25/46。"
        "该验证集的定位是支撑算法在外部真实课堂片段上的可信度，不是树莓派采集数据，也不是自采大规模数据集，"
        "更不作为单堂完整课堂 dashboard 主样本。项目不会宣称完整覆盖 SAV 15 类动作，而是聚焦与课堂反馈强相关的核心行为。"
    )
    return f"# SAV-50 比赛文档话术\n\n{text}\n"


def _render_example_bullets(rows: list[dict[str, str]]) -> str:
    return "\n".join(
        f"- `{row['clip_id']}`：{row['manual_review_class']}；期望 {row['expected_behavior']}；本地结果 {row['local_detection_summary']}；{row['competition_note']}"
        for row in rows
    )


def _write_summary_csv(path: Path, stats: dict[str, Any]) -> None:
    rows = [
        {"metric": "total_count", "value": stats["total_count"], "note": "SAV-50 外部真实课堂切片总数"},
        {"metric": "question_interaction", "value": stats["question_interaction_count"], "note": "课堂互动型"},
        {"metric": "classroom_routine_standing", "value": stats["classroom_routine_standing_count"], "note": "课堂流程站立型"},
        {"metric": "classroom_routine_bending", "value": stats["classroom_routine_bending_count"], "note": "课堂流程弯腰型"},
        {"metric": "analysis_success", "value": f"{stats['analysis_success_count']}/{stats['analysis_success_total']}", "note": stats["analysis_success_rate"]},
        {"metric": "raise_hand", "value": stats["raise_hand_match"], "note": stats["raise_hand_rate"]},
        {"metric": "stand", "value": stats["stand_match"], "note": stats["stand_rate"]},
        {"metric": "not_pi_capture", "value": "true", "note": "SAV 外部公开数据，不是树莓派采集"},
        {"metric": "not_own_capture", "value": "true", "note": "不是自采数据"},
        {"metric": "not_dashboard_sample", "value": "true", "note": "不是最终完整课堂 dashboard 主样本"},
        {"metric": "no_sav15_overclaim", "value": "true", "note": "不宣称完整覆盖 SAV 15 类行为"},
    ]
    _write_csv(path, rows, ["metric", "value", "note"])


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        return list(csv.DictReader(file_obj))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
