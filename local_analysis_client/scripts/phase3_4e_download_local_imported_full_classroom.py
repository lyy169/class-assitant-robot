from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
SAMPLE_ID = "local_imported_sav_full_classroom_20200908_17"
SOURCE_VIDEO_ID = "20200908_17"
MANIFEST_FIELDS = (
    "sample_id",
    "source_video_id",
    "video_path",
    "source_dataset",
    "source_type",
    "sample_type",
    "is_pi_capture",
    "is_own_capture",
    "is_local_processed",
    "expected_key_event_note",
    "created_at",
    "video_link",
    "link_found",
    "download_status",
    "video_size_bytes",
    "duration_seconds",
    "analysis_package_dir",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the Phase 3.4e local imported SAV full-classroom video.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--timeout-sec", type=int, default=7200)
    args = parser.parse_args()

    _refresh_windows_path()
    sample_root = args.sample_root.resolve()
    reports_dir = sample_root / "reports"
    videos_dir = sample_root / "videos"
    manifest_csv = reports_dir / "local_imported_full_classroom_manifest.csv"
    target_video = videos_dir / f"{SAMPLE_ID}.mp4"
    reports_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    row = _read_first_row(manifest_csv)
    if not row:
        row = _default_manifest_row(target_video=target_video, sample_root=sample_root)
    video_link = _find_video_link(args.sav_root.resolve())
    link_found = bool(video_link)
    yt_dlp_available = _tool_available("yt-dlp", ["yt-dlp", "--version"])
    ffmpeg_available = _tool_available("ffmpeg", ["ffmpeg", "-version"])
    notes: list[str] = []

    if target_video.exists():
        download_status = "existing"
    elif not link_found:
        download_status = "failed_no_video_link"
        notes.append("video_link_not_found")
    elif not yt_dlp_available:
        download_status = "failed_no_ytdlp"
        notes.append("yt_dlp_not_available")
    else:
        download_status = _download_video(target_video=target_video, video_link=video_link, timeout_sec=args.timeout_sec, notes=notes)

    duration_seconds = _probe_duration_seconds(target_video) if target_video.exists() else 0
    row.update(
        {
            "video_path": str(target_video),
            "video_link": video_link,
            "link_found": _bool_text(link_found),
            "download_status": download_status,
            "video_size_bytes": str(target_video.stat().st_size) if target_video.exists() else "",
            "duration_seconds": str(duration_seconds) if duration_seconds else "",
        }
    )
    _write_rows(manifest_csv, [row])
    ok = target_video.exists()
    print(f"PHASE34E_LOCAL_IMPORTED_YTDLP_AVAILABLE={_bool_text(yt_dlp_available)}")
    print(f"PHASE34E_LOCAL_IMPORTED_FFMPEG_AVAILABLE={_bool_text(ffmpeg_available)}")
    print(f"PHASE34E_LOCAL_IMPORTED_VIDEO_LINK_FOUND={_bool_text(link_found)}")
    print(f"PHASE34E_LOCAL_IMPORTED_DOWNLOAD_STATUS={download_status}")
    print(f"PHASE34E_LOCAL_IMPORTED_VIDEO_PRESENT={_bool_text(ok)}")
    print(f"PHASE34E_LOCAL_IMPORTED_VIDEO_PATH={target_video}")
    print(f"PHASE34E_LOCAL_IMPORTED_VIDEO_SIZE_BYTES={target_video.stat().st_size if target_video.exists() else 0}")
    print(f"PHASE34E_LOCAL_IMPORTED_DURATION_SECONDS={duration_seconds}")
    if notes:
        print(f"PHASE34E_LOCAL_IMPORTED_DOWNLOAD_NOTES={';'.join(notes)}")
    return 0 if ok else 1


def _find_video_link(sav_root: Path) -> str:
    candidates = (
        sav_root / "reports" / "selected_sav_video_links.csv",
        sav_root / "reports" / "selected_sav50_video_links.csv",
    )
    for path in candidates:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                if row.get("source_video_id") == SOURCE_VIDEO_ID and row.get("video_link"):
                    return str(row["video_link"])
    return ""


def _download_video(*, target_video: Path, video_link: str, timeout_sec: int, notes: list[str]) -> str:
    target_video.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "yt-dlp",
        "--socket-timeout",
        "30",
        "--retries",
        "3",
        "--fragment-retries",
        "3",
        "--merge-output-format",
        "mp4",
        "-o",
        str(target_video),
        video_link,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_sec)
    except (OSError, subprocess.SubprocessError) as exc:
        notes.append(f"download_exception={type(exc).__name__}")
        return "failed"
    if result.returncode == 0 and target_video.exists():
        return "downloaded"
    if result.stderr:
        notes.append(" ".join(result.stderr.strip().split())[:300])
    return "failed"


def _default_manifest_row(*, target_video: Path, sample_root: Path) -> dict[str, str]:
    return {
        "sample_id": SAMPLE_ID,
        "source_video_id": SOURCE_VIDEO_ID,
        "video_path": str(target_video),
        "source_dataset": "SAV",
        "source_type": "local_imported_video",
        "sample_type": "external_full_classroom_video",
        "is_pi_capture": "false",
        "is_own_capture": "false",
        "is_local_processed": "true",
        "expected_key_event_note": "16:27.5-16:30.5 contains many raised hands and a few standing students",
        "created_at": "",
        "analysis_package_dir": str(sample_root / "packages" / SAMPLE_ID),
    }


def _read_first_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return rows[0] if rows else {}


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in MANIFEST_FIELDS})


def _probe_duration_seconds(video_path: Path) -> int:
    if not video_path.exists():
        return 0
    try:
        import cv2

        capture = cv2.VideoCapture(str(video_path))
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
            if fps > 0 and frame_count > 0:
                return max(1, int(frame_count / fps))
        finally:
            capture.release()
    except Exception:
        return 0
    return 0


def _tool_available(name: str, command: list[str]) -> bool:
    if shutil.which(name) is None:
        return False
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _refresh_windows_path() -> None:
    if os.name != "nt":
        return
    current_path = os.environ.get("PATH", "")
    try:
        import winreg

        user_path = _read_registry_path(winreg.HKEY_CURRENT_USER, r"Environment")
        system_path = _read_registry_path(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        )
    except OSError:
        return
    os.environ["PATH"] = ";".join(part for part in (current_path, system_path, user_path) if part)


def _read_registry_path(root: Any, subkey: str) -> str:
    import winreg

    try:
        with winreg.OpenKey(root, subkey) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return str(value)
    except OSError:
        return ""


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
