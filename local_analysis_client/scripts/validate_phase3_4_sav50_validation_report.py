from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4 SAV-50 validation report outputs.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    args = parser.parse_args()

    reports_dir = args.sav_root.resolve() / "reports"
    report_md = reports_dir / "sav50_validation_report.md"
    detection_summary_csv = reports_dir / "sav50_detection_summary.csv"
    hit_miss_examples_csv = reports_dir / "sav50_hit_miss_examples.csv"

    report_present = report_md.exists()
    summary_present = detection_summary_csv.exists()
    examples_present = hit_miss_examples_csv.exists()
    report_text = report_md.read_text(encoding="utf-8") if report_present else ""
    summary_rows = _read_rows(detection_summary_csv) if summary_present else []
    example_rows = _read_rows(hit_miss_examples_csv) if examples_present else []

    report_content_ok = all(
        token in report_text
        for token in (
            "Phase 3.4",
            "SAV-50",
            "external_real_clip",
            "raise_hand",
            "stand",
            "不宣称完整识别 SAV 15 类动作",
        )
    )
    summary_metrics_ok = _summary_metrics_ok(summary_rows)
    examples_ok = bool(example_rows)
    ok = report_present and summary_present and examples_present and report_content_ok and summary_metrics_ok and examples_ok

    print(f"PHASE34_SAV50_REPORT_PRESENT={_bool_text(report_present)}")
    print(f"PHASE34_SAV50_DETECTION_SUMMARY_PRESENT={_bool_text(summary_present)}")
    print(f"PHASE34_SAV50_HIT_MISS_EXAMPLES_PRESENT={_bool_text(examples_present)}")
    print(f"PHASE34_SAV50_REPORT_CONTENT_OK={_bool_text(report_content_ok)}")
    print(f"PHASE34_SAV50_SUMMARY_METRICS_OK={_bool_text(summary_metrics_ok)}")
    print(f"PHASE34_SAV50_HIT_MISS_EXAMPLES_OK={_bool_text(examples_ok)}")
    print(f"PHASE34_SAV50_VALIDATION_REPORT_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _summary_metrics_ok(rows: list[dict[str, str]]) -> bool:
    by_metric = {row.get("metric"): row for row in rows}
    raise_hand = by_metric.get("raise_hand", {})
    stand = by_metric.get("stand", {})
    return (
        raise_hand.get("expected_count") == "29"
        and raise_hand.get("matched_count") == "16"
        and stand.get("expected_count") == "46"
        and stand.get("matched_count") == "25"
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
