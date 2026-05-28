from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
from collections import OrderedDict
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
STATUS_FIELDS = (
    "clip_id",
    "source_video_id",
    "phase34_category",
    "candidate_origin",
    "official_start_sec",
    "official_end_sec",
    "clip_start_sec",
    "clip_end_sec",
    "clip_duration_sec",
    "source_video_path",
    "manual_clip_path",
    "video_link",
    "download_status",
    "clip_status",
    "source_preexisting",
    "source_deleted",
    "source_delete_mode",
    "source_delete_error",
    "notes",
)
DELETE_MODE_NONE = "none"
DELETE_MODE_AFTER_ATTEMPT = "after_attempt"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and clip SAV-50 new Phase 3.4b candidates.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--clip-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--delete-source-after-attempt", action="store_true")
    parser.add_argument("--clip-padding-sec", type=float, default=10.0)
    parser.add_argument("--download-timeout-sec", type=int, default=900)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    source_videos_dir = sav_root / "source_videos"
    manual_clips_dir = sav_root / "manual_clips"
    candidates_csv = reports_dir / "selected_sav50_candidates.csv"
    video_links_csv = reports_dir / "selected_sav50_video_links.csv"
    status_csv = reports_dir / "sav50_clip_download_status.csv"

    source_videos_dir.mkdir(parents=True, exist_ok=True)
    manual_clips_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    _refresh_windows_path()
    yt_dlp_available = _tool_available("yt-dlp", ["yt-dlp", "--version"])
    ffmpeg_available = _tool_available("ffmpeg", ["ffmpeg", "-version"])
    print(f"PHASE34_SAV50_YTDLP_AVAILABLE={_bool_text(yt_dlp_available)}")
    print(f"PHASE34_SAV50_FFMPEG_AVAILABLE={_bool_text(ffmpeg_available)}")

    if not candidates_csv.exists() or not video_links_csv.exists():
        _write_rows(status_csv, [])
        _print_markers([], status_csv=status_csv, ok=False)
        return 1

    candidates = _select_candidates(_read_rows(candidates_csv), clip_ids=args.clip_id, limit=args.limit)
    grouped = _group_by_source(candidates)
    video_links = {str(row.get("source_video_id") or ""): str(row.get("video_link") or "") for row in _read_rows(video_links_csv)}
    delete_mode = DELETE_MODE_AFTER_ATTEMPT if args.delete_source_after_attempt else DELETE_MODE_NONE
    status_rows: list[dict[str, str]] = []

    for source_video_id, source_candidates in grouped.items():
        status_rows.extend(
            _process_source_group(
                source_video_id=source_video_id,
                candidates=source_candidates,
                video_link=video_links.get(source_video_id, ""),
                source_videos_dir=source_videos_dir,
                manual_clips_dir=manual_clips_dir,
                yt_dlp_available=yt_dlp_available,
                ffmpeg_available=ffmpeg_available,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                delete_mode=delete_mode,
                clip_padding_sec=args.clip_padding_sec,
                download_timeout_sec=args.download_timeout_sec,
            )
        )
        _write_rows(status_csv, status_rows)

    _write_rows(status_csv, status_rows)
    ok = bool(status_rows) if args.dry_run else any(row.get("clip_status") in {"existing", "created"} for row in status_rows)
    _print_markers(status_rows, status_csv=status_csv, ok=ok)
    return 0 if ok else 1


def _select_candidates(rows: list[dict[str, str]], *, clip_ids: list[str], limit: int | None) -> list[dict[str, str]]:
    selected = [row for row in rows if row.get("candidate_origin") == "sav50_auto_selected"]
    if clip_ids:
        selected_ids = set(clip_ids)
        selected = [row for row in selected if str(row.get("clip_id") or "") in selected_ids]
    if limit is not None:
        selected = selected[: max(limit, 0)]
    return selected


def _group_by_source(rows: list[dict[str, str]]) -> OrderedDict[str, list[dict[str, str]]]:
    grouped: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for row in rows:
        source_video_id = str(row.get("source_video_id") or "")
        if source_video_id:
            grouped.setdefault(source_video_id, []).append(row)
    return grouped


def _process_source_group(
    *,
    source_video_id: str,
    candidates: list[dict[str, str]],
    video_link: str,
    source_videos_dir: Path,
    manual_clips_dir: Path,
    yt_dlp_available: bool,
    ffmpeg_available: bool,
    overwrite: bool,
    dry_run: bool,
    delete_mode: str,
    clip_padding_sec: float,
    download_timeout_sec: int,
) -> list[dict[str, str]]:
    source_video_path = source_videos_dir / f"{source_video_id}.mp4"
    source_preexisting = source_video_path.exists()
    notes: list[str] = []
    if _all_group_clips_exist(candidates, manual_clips_dir) and not overwrite:
        download_status = "skipped_all_clips_existing"
    else:
        download_status = _resolve_download_status(
            source_video_path=source_video_path,
            video_link=video_link,
            yt_dlp_available=yt_dlp_available,
            overwrite=overwrite,
            dry_run=dry_run,
            notes=notes,
        )
        if download_status == "download_required":
            download_status = _download_source_video(source_video_path, video_link, notes, timeout_sec=download_timeout_sec)

    rows = [
        _process_clip(
            candidate=candidate,
            source_video_path=source_video_path,
            manual_clips_dir=manual_clips_dir,
            video_link=video_link,
            download_status=download_status,
            source_preexisting=source_preexisting,
            ffmpeg_available=ffmpeg_available,
            overwrite=overwrite,
            dry_run=dry_run,
            delete_mode=delete_mode,
            clip_padding_sec=clip_padding_sec,
            source_notes=notes,
        )
        for candidate in candidates
    ]

    source_deleted = False
    source_delete_error = ""
    if delete_mode == DELETE_MODE_AFTER_ATTEMPT:
        source_deleted, source_delete_error = _delete_source_if_allowed(
            source_video_path=source_video_path,
            source_videos_dir=source_videos_dir,
            source_video_id=source_video_id,
            dry_run=dry_run,
        )
    for row in rows:
        row["source_deleted"] = _bool_text(source_deleted)
        row["source_delete_error"] = source_delete_error
    return rows


def _all_group_clips_exist(candidates: list[dict[str, str]], manual_clips_dir: Path) -> bool:
    return bool(candidates) and all((manual_clips_dir / f"{str(candidate.get('clip_id') or '')}.mp4").exists() for candidate in candidates)


def _process_clip(
    *,
    candidate: dict[str, str],
    source_video_path: Path,
    manual_clips_dir: Path,
    video_link: str,
    download_status: str,
    source_preexisting: bool,
    ffmpeg_available: bool,
    overwrite: bool,
    dry_run: bool,
    delete_mode: str,
    clip_padding_sec: float,
    source_notes: list[str],
) -> dict[str, str]:
    clip_id = str(candidate.get("clip_id") or "")
    start_sec = _safe_float(candidate.get("start_sec")) or 0.0
    end_sec = _safe_float(candidate.get("end_sec")) or start_sec
    clip_start_sec = max(start_sec - clip_padding_sec, 0.0)
    clip_end_sec = end_sec + clip_padding_sec
    clip_duration_sec = max(clip_end_sec - clip_start_sec, 0.0)
    manual_clip_path = manual_clips_dir / f"{clip_id}.mp4"
    notes = list(source_notes)
    source_ready = source_video_path.exists() or download_status in {"existing", "downloaded", "dry_run_download_planned"}
    clip_status = _resolve_clip_status(
        source_video_path=source_video_path,
        manual_clip_path=manual_clip_path,
        ffmpeg_available=ffmpeg_available,
        overwrite=overwrite,
        dry_run=dry_run,
        source_ready=source_ready,
        notes=notes,
    )
    if clip_status == "clip_required":
        clip_status = _create_clip(
            source_video_path=source_video_path,
            manual_clip_path=manual_clip_path,
            clip_start_sec=clip_start_sec,
            clip_duration_sec=clip_duration_sec,
            notes=notes,
        )

    return {
        "clip_id": clip_id,
        "source_video_id": str(candidate.get("source_video_id") or ""),
        "phase34_category": str(candidate.get("phase34_category") or ""),
        "candidate_origin": str(candidate.get("candidate_origin") or ""),
        "official_start_sec": _format_seconds(start_sec),
        "official_end_sec": _format_seconds(end_sec),
        "clip_start_sec": _format_seconds(clip_start_sec),
        "clip_end_sec": _format_seconds(clip_end_sec),
        "clip_duration_sec": _format_seconds(clip_duration_sec),
        "source_video_path": str(source_video_path),
        "manual_clip_path": str(manual_clip_path),
        "video_link": video_link,
        "download_status": download_status,
        "clip_status": clip_status,
        "source_preexisting": _bool_text(source_preexisting),
        "source_deleted": "false",
        "source_delete_mode": delete_mode,
        "source_delete_error": "",
        "notes": ";".join(dict.fromkeys(note for note in notes if note)),
    }


def _resolve_download_status(
    *,
    source_video_path: Path,
    video_link: str,
    yt_dlp_available: bool,
    overwrite: bool,
    dry_run: bool,
    notes: list[str],
) -> str:
    if source_video_path.exists() and not overwrite:
        return "existing"
    if not video_link:
        notes.append("manual_download_required")
        return "skipped_no_video_link"
    if not yt_dlp_available:
        notes.append("manual_download_required")
        return "skipped_no_ytdlp"
    return "dry_run_download_planned" if dry_run else "download_required"


def _resolve_clip_status(
    *,
    source_video_path: Path,
    manual_clip_path: Path,
    ffmpeg_available: bool,
    overwrite: bool,
    dry_run: bool,
    source_ready: bool,
    notes: list[str],
) -> str:
    if manual_clip_path.exists() and not overwrite:
        return "existing"
    if not source_ready:
        notes.append("manual_download_required")
        return "skipped_no_source_video"
    if not ffmpeg_available:
        return "skipped_no_ffmpeg"
    return "dry_run_clip_planned" if dry_run else "clip_required"


def _download_source_video(source_video_path: Path, video_link: str, notes: list[str], *, timeout_sec: int) -> str:
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--socket-timeout",
                "30",
                "--retries",
                "2",
                "--fragment-retries",
                "2",
                "-o",
                str(source_video_path),
                video_link,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        notes.append("manual_download_required")
        notes.append(f"download_error={type(exc).__name__}")
        return "failed"
    if result.returncode == 0 and source_video_path.exists():
        return "downloaded"
    notes.append("manual_download_required")
    if result.stderr:
        notes.append(_compact_note(result.stderr))
    return "failed"


def _create_clip(
    *,
    source_video_path: Path,
    manual_clip_path: Path,
    clip_start_sec: float,
    clip_duration_sec: float,
    notes: list[str],
) -> str:
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        _format_seconds(clip_start_sec),
        "-i",
        str(source_video_path),
        "-t",
        _format_seconds(clip_duration_sec),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(manual_clip_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.SubprocessError) as exc:
        notes.append(f"clip_error={type(exc).__name__}")
        return "failed"
    if result.returncode == 0 and manual_clip_path.exists():
        return "created"
    if result.stderr:
        notes.append(_compact_note(result.stderr))
    return "failed"


def _delete_source_if_allowed(*, source_video_path: Path, source_videos_dir: Path, source_video_id: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run or not source_video_path.exists():
        return False, ""
    safe, error = _validate_source_delete_path(source_video_path, source_videos_dir, source_video_id)
    if not safe:
        return False, error
    try:
        source_video_path.unlink()
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def _validate_source_delete_path(source_video_path: Path, source_videos_dir: Path, source_video_id: str) -> tuple[bool, str]:
    expected_name = f"{source_video_id}.mp4"
    source_path = source_video_path.resolve(strict=False)
    source_dir = source_videos_dir.resolve(strict=False)
    if source_video_path.name != expected_name:
        return False, f"unexpected_source_filename: {source_video_path.name}"
    if source_path.parent != source_dir:
        return False, f"source_path_outside_source_videos: {source_path}"
    return True, ""


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


def _read_registry_path(root: int, subkey: str) -> str:
    import winreg

    try:
        with winreg.OpenKey(root, subkey) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return str(value)
    except OSError:
        return ""


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=STATUS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in STATUS_FIELDS})


def _print_markers(rows: list[dict[str, str]], *, status_csv: Path, ok: bool) -> None:
    by_source: OrderedDict[str, dict[str, str]] = OrderedDict()
    for row in rows:
        by_source.setdefault(str(row.get("source_video_id") or ""), row)
    print(f"PHASE34_SAV50_DOWNLOAD_CLIP_PLAN_COUNT={len(rows)}")
    print(f"PHASE34_SAV50_SOURCE_VIDEO_EXISTING_COUNT={sum(1 for row in by_source.values() if row.get('download_status') == 'existing')}")
    print(f"PHASE34_SAV50_SOURCE_VIDEO_DOWNLOADED_COUNT={sum(1 for row in by_source.values() if row.get('download_status') == 'downloaded')}")
    print(f"PHASE34_SAV50_SOURCE_VIDEO_FAILED_COUNT={sum(1 for row in by_source.values() if row.get('download_status') == 'failed')}")
    print(f"PHASE34_SAV50_CLIP_EXISTING_COUNT={sum(1 for row in rows if row.get('clip_status') == 'existing')}")
    print(f"PHASE34_SAV50_CLIP_CREATED_COUNT={sum(1 for row in rows if row.get('clip_status') == 'created')}")
    print(f"PHASE34_SAV50_CLIP_FAILED_COUNT={sum(1 for row in rows if row.get('clip_status') == 'failed')}")
    print(f"PHASE34_SAV50_CLIP_SKIPPED_COUNT={sum(1 for row in rows if str(row.get('clip_status') or '').startswith('skipped_'))}")
    print(f"PHASE34_SAV50_SOURCE_VIDEO_DELETED_COUNT={sum(1 for row in by_source.values() if row.get('source_deleted') == 'true')}")
    print(f"PHASE34_SAV50_SOURCE_VIDEO_DELETE_FAILED_COUNT={sum(1 for row in by_source.values() if row.get('source_delete_error'))}")
    print(f"PHASE34_SAV50_CLIP_STATUS_CSV={status_csv}")
    print(f"PHASE34_SAV50_DOWNLOAD_AND_CLIP_OK={_bool_text(ok)}")


def _safe_float(value: str | None) -> float | None:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return None


def _format_seconds(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _compact_note(value: str) -> str:
    return " ".join(value.strip().split())[:240]


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
