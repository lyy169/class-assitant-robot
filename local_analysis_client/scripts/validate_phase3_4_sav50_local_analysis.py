from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
SOURCE_FIELDS = {
    "source_name": "SAV",
    "source_type": "public_dataset",
    "data_mode": "external_real_clip",
    "is_demo": "false",
    "is_own_capture": "false",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4 SAV-50 local analysis outputs.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    manifest_csv = reports_dir / "sav50_clip_packages_manifest.csv"
    analysis_status_csv = reports_dir / "sav50_local_analysis_status.csv"
    comparison_csv = reports_dir / "sav50_local_comparison.csv"
    comparison_summary_json = reports_dir / "sav50_local_comparison_summary.json"

    manifest_present = manifest_csv.exists()
    status_present = analysis_status_csv.exists()
    comparison_present = comparison_csv.exists()
    summary_present = comparison_summary_json.exists()
    manifest_rows = _read_rows(manifest_csv) if manifest_present else []
    status_rows = _read_rows(analysis_status_csv) if status_present else []
    comparison_rows = _read_rows(comparison_csv) if comparison_present else []
    summary = _read_json(comparison_summary_json) if summary_present else {}

    package_count = len(manifest_rows)
    source_marked = _source_marked(manifest_rows) and _source_marked(status_rows) and _result_json_source_marked(status_rows)
    local_result_count = int(summary.get("local_result_count") or sum(1 for row in comparison_rows if row.get("local_result_present") == "true"))
    failed_rows_have_reason = all(row.get("error") for row in status_rows if row.get("analysis_status") == "failed")
    ok = (
        manifest_present
        and package_count == 50
        and status_present
        and comparison_present
        and summary_present
        and source_marked
        and local_result_count >= 1
        and failed_rows_have_reason
    )

    print(f"PHASE34_SAV50_PACKAGE_MANIFEST_PRESENT={_bool_text(manifest_present)}")
    print(f"PHASE34_SAV50_PACKAGE_COUNT={package_count}")
    print(f"PHASE34_SAV50_ANALYSIS_STATUS_PRESENT={_bool_text(status_present)}")
    print(f"PHASE34_SAV50_COMPARISON_PRESENT={_bool_text(comparison_present)}")
    print(f"PHASE34_SAV50_COMPARISON_SUMMARY_PRESENT={_bool_text(summary_present)}")
    print(f"PHASE34_SAV50_SOURCE_MARKED={_bool_text(source_marked)}")
    print(f"PHASE34_SAV50_LOCAL_RESULT_COUNT={local_result_count}")
    print(f"PHASE34_SAV50_LOCAL_ANALYSIS_VALIDATION_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _source_marked(rows: list[dict[str, str]]) -> bool:
    return bool(rows) and all(
        all(str(row.get(field) or "") == expected for field, expected in SOURCE_FIELDS.items())
        for row in rows
    )


def _result_json_source_marked(status_rows: list[dict[str, str]]) -> bool:
    successful_rows = [row for row in status_rows if row.get("analysis_status") == "success"]
    if not successful_rows:
        return False
    for row in successful_rows:
        result_path = Path(str(row.get("result_json") or ""))
        payload = _read_json(result_path) if result_path.exists() else {}
        if not payload:
            return False
        if payload.get("source_name") != "SAV":
            return False
        if payload.get("source_type") != "public_dataset":
            return False
        if payload.get("data_mode") != "external_real_clip":
            return False
        if payload.get("is_demo") is not False:
            return False
        if payload.get("is_own_capture") is not False:
            return False
        phase34_sav = payload.get("phase34_sav") if isinstance(payload.get("phase34_sav"), dict) else {}
        if phase34_sav.get("source_name") != "SAV":
            return False
        if not phase34_sav.get("clip_id"):
            return False
    return True


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
