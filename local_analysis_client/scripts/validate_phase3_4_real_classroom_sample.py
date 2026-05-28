from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SOURCE_NAME = "local_real_classroom_sample"
SOURCE_TYPE = "own_real_classroom_session"
DATA_MODE = "local_real_classroom_session"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4e real classroom sample outputs.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    reports_dir = sample_root / "reports"
    manifest_csv = reports_dir / "real_classroom_sample_manifest.csv"
    status_csv = reports_dir / "real_classroom_analysis_status.csv"
    report_md = reports_dir / "real_classroom_validation_report.md"

    workspace_present = sample_root.exists() and reports_dir.exists() and (sample_root / "analysis_results").exists()
    manifest_present = manifest_csv.exists()
    status_present = status_csv.exists()
    report_present = report_md.exists()
    manifest_rows = _read_rows(manifest_csv) if manifest_present else []
    status_rows = _read_rows(status_csv) if status_present else []
    video_present = bool(manifest_rows and Path(str(manifest_rows[0].get("source_video_path") or "")).exists())
    source_marked = _source_marked(manifest_rows, status_rows)
    ok = workspace_present and video_present and manifest_present and status_present and report_present and source_marked

    print(f"PHASE34_REAL_CLASSROOM_WORKSPACE_PRESENT={_bool_text(workspace_present)}")
    print(f"PHASE34_REAL_CLASSROOM_VIDEO_PRESENT={_bool_text(video_present)}")
    print(f"PHASE34_REAL_CLASSROOM_MANIFEST_PRESENT={_bool_text(manifest_present)}")
    print(f"PHASE34_REAL_CLASSROOM_ANALYSIS_STATUS_PRESENT={_bool_text(status_present)}")
    print(f"PHASE34_REAL_CLASSROOM_REPORT_PRESENT={_bool_text(report_present)}")
    print(f"PHASE34_REAL_CLASSROOM_SOURCE_MARKED={_bool_text(source_marked)}")
    print(f"PHASE34_REAL_CLASSROOM_VALIDATION_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _source_marked(manifest_rows: list[dict[str, str]], status_rows: list[dict[str, str]]) -> bool:
    if not manifest_rows:
        return False
    rows_to_check = [manifest_rows[0]]
    if status_rows:
        rows_to_check.append(status_rows[0])
    for row in rows_to_check:
        if row.get("source_name") != SOURCE_NAME:
            return False
        if row.get("source_type") != SOURCE_TYPE:
            return False
        if row.get("data_mode") != DATA_MODE:
            return False
        if row.get("is_demo") != "false":
            return False
        if row.get("is_own_capture") != "true":
            return False
    if status_rows and status_rows[0].get("analysis_status") == "success":
        result_path = Path(str(status_rows[0].get("result_json") or ""))
        payload = _read_json(result_path)
        return (
            payload.get("source_name") == SOURCE_NAME
            and payload.get("source_type") == SOURCE_TYPE
            and payload.get("data_mode") == DATA_MODE
            and payload.get("is_demo") is False
            and payload.get("is_own_capture") is True
            and isinstance(payload.get("phase34_real_classroom"), dict)
        )
    return True


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
