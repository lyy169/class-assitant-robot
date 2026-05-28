from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SAMPLE_ID = "local_imported_sav_full_classroom_20200908_17"
SOURCE_VIDEO_ID = "20200908_17"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4e local imported SAV full-classroom outputs.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    videos_dir = sample_root / "videos"
    reports_dir = sample_root / "reports"
    analysis_results_dir = sample_root / "analysis_results"
    video_path = videos_dir / f"{SAMPLE_ID}.mp4"
    manifest_csv = reports_dir / "local_imported_full_classroom_manifest.csv"
    status_csv = reports_dir / "local_imported_full_classroom_analysis_status.csv"
    report_md = reports_dir / "local_imported_full_classroom_validation_report.md"
    summary_csv = reports_dir / "local_imported_full_classroom_summary.csv"

    workspace_present = sample_root.exists() and videos_dir.exists() and reports_dir.exists() and analysis_results_dir.exists()
    video_present = video_path.exists()
    manifest_present = manifest_csv.exists()
    status_present = status_csv.exists()
    report_present = report_md.exists()
    manifest = _read_first_row(manifest_csv)
    status = _read_first_row(status_csv)
    result_payload = _read_json(Path(str(status.get("result_json") or ""))) if status.get("result_json") else {}
    source_marked = _source_marked(manifest, status, result_payload)
    not_pi = manifest.get("is_pi_capture") == "false" and status.get("is_pi_capture", "false") == "false"
    not_own = manifest.get("is_own_capture") == "false" and status.get("is_own_capture", "false") == "false"
    analysis_success = status.get("analysis_status") == "success"
    report_content_ok = _report_content_ok(report_md) if report_present else False
    ok = (
        workspace_present
        and video_present
        and manifest_present
        and source_marked
        and not_pi
        and not_own
        and status_present
        and analysis_success
        and report_present
        and summary_csv.exists()
        and report_content_ok
    )

    print(f"PHASE34E_LOCAL_IMPORTED_WORKSPACE_PRESENT={_bool_text(workspace_present)}")
    print(f"PHASE34E_LOCAL_IMPORTED_VIDEO_PRESENT={_bool_text(video_present)}")
    print(f"PHASE34E_LOCAL_IMPORTED_MANIFEST_PRESENT={_bool_text(manifest_present)}")
    print(f"PHASE34E_LOCAL_IMPORTED_SOURCE_MARKED={_bool_text(source_marked)}")
    print(f"PHASE34E_LOCAL_IMPORTED_NOT_PI_CAPTURE={_bool_text(not_pi)}")
    print(f"PHASE34E_LOCAL_IMPORTED_NOT_OWN_CAPTURE={_bool_text(not_own)}")
    print(f"PHASE34E_LOCAL_IMPORTED_ANALYSIS_STATUS_PRESENT={_bool_text(status_present)}")
    print(f"PHASE34E_LOCAL_IMPORTED_ANALYSIS_SUCCESS={_bool_text(analysis_success)}")
    print(f"PHASE34E_LOCAL_IMPORTED_REPORT_PRESENT={_bool_text(report_present)}")
    print(f"PHASE34E_LOCAL_IMPORTED_REPORT_CONTENT_OK={_bool_text(report_content_ok)}")
    print(f"PHASE34E_LOCAL_IMPORTED_FULL_CLASSROOM_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _source_marked(manifest: dict[str, str], status: dict[str, str], result_payload: dict[str, object]) -> bool:
    expected = {
        "source_dataset": "SAV",
        "source_type": "local_imported_video",
        "sample_type": "external_full_classroom_video",
        "is_pi_capture": "false",
        "is_own_capture": "false",
        "is_local_processed": "true",
    }
    for row in (manifest, status):
        if not row:
            return False
        for key, value in expected.items():
            if row.get(key) != value:
                return False
    if result_payload:
        if result_payload.get("source_dataset") != "SAV":
            return False
        if result_payload.get("source_type") != "local_imported_video":
            return False
        if result_payload.get("sample_type") != "external_full_classroom_video":
            return False
        if result_payload.get("is_pi_capture") is not False:
            return False
        if result_payload.get("is_own_capture") is not False:
            return False
        if result_payload.get("is_local_processed") is not True:
            return False
    return True


def _report_content_ok(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    required = (
        "Phase 3.4e 本地导入完整课堂视频分析报告",
        "SAV 公开数据集完整课堂视频",
        "不是树莓派采集",
        "不是项目自采集数据",
        "source_type=local_imported_video",
        "sample_type=external_full_classroom_video",
        "16:27.5-16:30.5",
        "不宣称完整识别 SAV 15 类动作",
        "50 个 SAV 外部真实课堂切片验证",
    )
    return all(item in text for item in required)


def _read_first_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return rows[0] if rows else {}


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
