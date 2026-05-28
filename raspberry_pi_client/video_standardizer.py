from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

try:
    from app_config import settings
except Exception:
    settings = None


def _setting(name: str, default):
    return getattr(settings, name, default) if settings is not None else default


FFPROBE_BIN = str(_setting("pi_ffprobe_bin", "ffprobe"))
FFMPEG_BIN = str(_setting("pi_ffmpeg_bin", "ffmpeg"))


@dataclass
class VideoStandardizationResult:
    raw_video_path: str
    standardized_video_path: str
    format: str = "unknown"
    codec: str = "unknown"
    audio_codec: str = "unknown"
    browser_compatible: bool = False
    transcode_status: str = "unknown"
    transcode_error: str = ""

    def as_metadata(self) -> dict:
        return asdict(self)


def _run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def probe_media(filepath: Path, ffprobe_bin: str = FFPROBE_BIN) -> Optional[dict]:
    command = [
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(filepath),
    ]
    try:
        result = _run_command(command, timeout=20)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None


def _extract_streams(media_info: dict) -> tuple[Optional[dict], Optional[dict]]:
    video_stream = None
    audio_stream = None
    for stream in media_info.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream
    return video_stream, audio_stream


def _get_int(stream: Optional[dict], key: str) -> int:
    if not stream:
        return 0
    try:
        return int(stream.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _format_name(media_info: Optional[dict]) -> str:
    if not media_info:
        return "unknown"
    format_name = ((media_info.get("format") or {}).get("format_name") or "").lower()
    if "mp4" in format_name:
        return "mp4"
    return format_name or "unknown"


def media_summary(media_info: Optional[dict]) -> dict:
    video_stream, audio_stream = _extract_streams(media_info or {})
    return {
        "format": _format_name(media_info),
        "codec": ((video_stream or {}).get("codec_name") or "unknown").lower(),
        "audio_codec": ((audio_stream or {}).get("codec_name") or "none").lower(),
        "pix_fmt": ((video_stream or {}).get("pix_fmt") or "unknown").lower(),
        "width": _get_int(video_stream, "width"),
        "height": _get_int(video_stream, "height"),
        "has_video": video_stream is not None,
    }


def is_browser_compatible(media_info: dict) -> bool:
    summary = media_summary(media_info)
    if not summary["has_video"]:
        return False
    dimensions_ok = (
        summary["width"] > 0
        and summary["height"] > 0
        and summary["width"] % 2 == 0
        and summary["height"] % 2 == 0
    )
    return (
        summary["format"] == "mp4"
        and summary["codec"] == "h264"
        and summary["audio_codec"] in {"aac", "none"}
        and summary["pix_fmt"] == "yuv420p"
        and dimensions_ok
    )


def _remux_faststart(input_path: Path, output_path: Path, ffmpeg_bin: str) -> tuple[bool, str]:
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    try:
        result = _run_command(command, timeout=300)
    except FileNotFoundError:
        return False, "ffmpeg_not_found"
    except subprocess.TimeoutExpired:
        return False, "ffmpeg_remux_timeout"
    if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
        return True, ""
    return False, (result.stderr or "ffmpeg_remux_failed")[-1500:]


def _transcode_h264(input_path: Path, output_path: Path, ffmpeg_bin: str) -> tuple[bool, str]:
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=25,format=yuv420p",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level:v",
        "4.1",
        "-g",
        "50",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        "-max_muxing_queue_size",
        "1024",
        str(output_path),
    ]
    try:
        result = _run_command(command, timeout=900)
    except FileNotFoundError:
        return False, "ffmpeg_not_found"
    except subprocess.TimeoutExpired:
        return False, "ffmpeg_transcode_timeout"
    if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
        return True, ""
    return False, (result.stderr or "ffmpeg_transcode_failed")[-1500:]


def _transcode_h264_with_audio(
    input_path: Path,
    audio_path: Path,
    output_path: Path,
    ffmpeg_bin: str,
) -> tuple[bool, str]:
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=25,format=yuv420p",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level:v",
        "4.1",
        "-g",
        "50",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-shortest",
        "-movflags",
        "+faststart",
        "-max_muxing_queue_size",
        "1024",
        str(output_path),
    ]
    try:
        result = _run_command(command, timeout=900)
    except FileNotFoundError:
        return False, "ffmpeg_not_found"
    except subprocess.TimeoutExpired:
        return False, "ffmpeg_transcode_timeout"
    if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
        return True, ""
    return False, (result.stderr or "ffmpeg_transcode_failed")[-1500:]


def _valid_audio_path(audio_path: Path | None) -> bool:
    return bool(audio_path and audio_path.exists() and audio_path.stat().st_size > 44)


def standardize_video(
    input_path: Path,
    output_path: Path | None = None,
    audio_path: Path | None = None,
    ffmpeg_bin: str = FFMPEG_BIN,
    ffprobe_bin: str = FFPROBE_BIN,
) -> VideoStandardizationResult:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path or input_path.with_name("standardized_video.mp4")).resolve()
    audio_path = Path(audio_path).resolve() if audio_path is not None else None

    result = VideoStandardizationResult(
        raw_video_path=str(input_path),
        standardized_video_path=str(output_path),
    )

    if not input_path.exists():
        result.transcode_status = "failed"
        result.transcode_error = f"raw_video_not_found:{input_path}"
        return result

    media_info = probe_media(input_path, ffprobe_bin=ffprobe_bin)
    summary = media_summary(media_info)
    result.format = summary["format"]
    result.codec = summary["codec"]
    result.audio_codec = summary["audio_codec"]

    if media_info is None or not summary["has_video"]:
        result.transcode_status = "failed"
        result.transcode_error = "ffprobe_failed_or_no_video_stream"
        return result

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if input_path == output_path:
        result.transcode_status = "failed"
        result.transcode_error = "output_path_must_not_equal_raw_video_path"
        return result

    if output_path.exists():
        try:
            output_path.unlink()
        except OSError as exc:
            result.transcode_status = "failed"
            result.transcode_error = f"cannot_replace_existing_output:{exc}"
            return result

    if _valid_audio_path(audio_path):
        ok, error = _transcode_h264_with_audio(input_path, audio_path, output_path, ffmpeg_bin)
        result.transcode_status = "success" if ok else "failed"
        result.transcode_error = error
    elif is_browser_compatible(media_info):
        ok, error = _remux_faststart(input_path, output_path, ffmpeg_bin)
        if not ok:
            try:
                shutil.copy2(input_path, output_path)
                ok = output_path.exists() and output_path.stat().st_size > 0
                error = "" if ok else error
            except OSError as exc:
                error = f"{error}; copy_fallback_failed:{exc}"
        result.transcode_status = "not_needed" if ok else "failed"
        result.transcode_error = error
    else:
        ok, error = _transcode_h264(input_path, output_path, ffmpeg_bin)
        result.transcode_status = "success" if ok else "failed"
        result.transcode_error = error

    standardized_info = probe_media(output_path, ffprobe_bin=ffprobe_bin) if output_path.exists() else None
    standardized_summary = media_summary(standardized_info)
    result.format = standardized_summary["format"]
    result.codec = standardized_summary["codec"]
    result.audio_codec = standardized_summary["audio_codec"]
    result.browser_compatible = bool(standardized_info and is_browser_compatible(standardized_info))

    if result.transcode_status != "failed" and not result.browser_compatible:
        result.transcode_status = "failed"
        result.transcode_error = result.transcode_error or "standardized_video_not_browser_compatible"

    return result
