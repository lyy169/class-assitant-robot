from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV\reports")

SOURCE_FILES = [
    "final_sav50_summary.json",
    "sav50_detection_summary.csv",
    "sav50_hit_miss_examples.csv",
    "final_sav50_manual_review_results.csv",
    "sav50_local_comparison.csv",
    "sav50_local_comparison_summary.json",
]
SUMMARY_MD = "sav50_competition_validation_summary.md"
SUMMARY_CSV = "sav50_competition_validation_summary.csv"
TALKING_POINTS = "sav50_competition_talking_points.md"
EXAMPLES_CSV = "sav50_competition_examples.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.9 SAV-50 competition validation outputs.")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    report_dir = args.report_dir.resolve()
    source_files_present = all((report_dir / name).exists() for name in SOURCE_FILES)
    summary = _read_json(report_dir / "final_sav50_summary.json")
    comparison_summary = _read_json(report_dir / "sav50_local_comparison_summary.json")
    summary_md = report_dir / SUMMARY_MD
    summary_csv = report_dir / SUMMARY_CSV
    talking_points = report_dir / TALKING_POINTS
    examples_csv = report_dir / EXAMPLES_CSV

    examples = _read_csv(examples_csv)
    hit_count = len([row for row in examples if row.get("example_type") == "hit"])
    miss_count = len([row for row in examples if row.get("example_type") == "miss"])
    md_text = _read_text(summary_md)
    talking_text = _read_text(talking_points)
    csv_text = _read_text(summary_csv)

    total_count = int(summary.get("total_count", 0))
    interaction_count = int(summary.get("question_interaction_count", 0))
    routine_standing_count = int(summary.get("classroom_routine_standing_count", 0))
    routine_bending_count = int(summary.get("classroom_routine_bending_count", 0))
    analysis_success_count = int(comparison_summary.get("local_result_count", 0))
    raise_hand_match = f"{comparison_summary.get('raise_hand_matched_count', 0)}/{comparison_summary.get('raise_hand_expected_count', 0)}"
    stand_match = f"{comparison_summary.get('stand_matched_count', 0)}/{comparison_summary.get('stand_expected_count', 0)}"

    not_pi_capture = _contains_all(md_text + csv_text + talking_text, ["非树莓派采集", "not_pi_capture"])
    not_own_capture = _contains_all(md_text + csv_text + talking_text, ["非自采", "not_own_capture"])
    not_dashboard = "非最终 dashboard 主样本" in md_text and "not_dashboard_sample" in csv_text
    no_sav15_overclaim = "不宣称完整覆盖 SAV 15 类行为" in md_text and "识别准确率达到 90% 以上" not in talking_text
    ready = (
        source_files_present
        and total_count == 50
        and interaction_count == 25
        and routine_standing_count == 15
        and routine_bending_count == 10
        and analysis_success_count == 50
        and raise_hand_match == "16/29"
        and stand_match == "25/46"
        and summary_md.exists()
        and summary_csv.exists()
        and talking_points.exists()
        and examples_csv.exists()
        and hit_count >= 3
        and miss_count >= 3
        and not_pi_capture
        and not_own_capture
        and not_dashboard
        and no_sav15_overclaim
    )

    print(f"PHASE39_SAV50_SOURCE_FILES_PRESENT={_bool_text(source_files_present)}")
    print(f"PHASE39_SAV50_TOTAL_COUNT={total_count}")
    print(f"PHASE39_SAV50_INTERACTION_COUNT={interaction_count}")
    print(f"PHASE39_SAV50_ROUTINE_STANDING_COUNT={routine_standing_count}")
    print(f"PHASE39_SAV50_ROUTINE_BENDING_COUNT={routine_bending_count}")
    print(f"PHASE39_SAV50_ANALYSIS_SUCCESS_COUNT={analysis_success_count}")
    print(f"PHASE39_SAV50_RAISE_HAND_MATCH={raise_hand_match}")
    print(f"PHASE39_SAV50_STAND_MATCH={stand_match}")
    print(f"PHASE39_SAV50_SUMMARY_MD_PRESENT={_bool_text(summary_md.exists())}")
    print(f"PHASE39_SAV50_SUMMARY_CSV_PRESENT={_bool_text(summary_csv.exists())}")
    print(f"PHASE39_SAV50_TALKING_POINTS_PRESENT={_bool_text(talking_points.exists())}")
    print(f"PHASE39_SAV50_EXAMPLES_PRESENT={_bool_text(examples_csv.exists())}")
    print(f"PHASE39_SAV50_HIT_EXAMPLES_COUNT>={hit_count}")
    print(f"PHASE39_SAV50_MISS_EXAMPLES_COUNT>={miss_count}")
    print(f"PHASE39_SAV50_NOT_PI_CAPTURE={_bool_text(not_pi_capture)}")
    print(f"PHASE39_SAV50_NOT_OWN_CAPTURE={_bool_text(not_own_capture)}")
    print(f"PHASE39_SAV50_NOT_FULL_CLASS_DASHBOARD_SAMPLE={_bool_text(not_dashboard)}")
    print(f"PHASE39_SAV50_NO_SAV15_OVERCLAIM={_bool_text(no_sav15_overclaim)}")
    print(f"PHASE39_SAV50_COMPETITION_VALIDATION_READY={_bool_text(ready)}")
    return 0 if ready else 1


def _contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
