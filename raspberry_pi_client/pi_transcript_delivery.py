from __future__ import annotations

import json
import logging
import os
import re
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

try:
    from app_config import settings
except Exception:
    settings = None


logger = logging.getLogger("pi_transcript_delivery")
CHAT_LOG_PATH = Path("Log/PI-Assistant.log")
CHAT_RECOGNIZE_PATTERN = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Recongnize result:(?P<text>.+)$"
)

AZURE_STT_URL = (
    "https://eastasia.stt.speech.microsoft.com/"
    "speech/recognition/conversation/cognitiveservices/v1?language=zh-CN"
)


def _setting(name: str, default):
    return getattr(settings, name, default) if settings is not None else default


def _normalize_text(value: str) -> str:
    text = (value or "").strip()
    return " ".join(text.split())


def _audio_duration(audio_path: Path) -> float:
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            frame_rate = wav_file.getframerate() or 16000
            frame_count = wav_file.getnframes()
            if frame_rate <= 0:
                return 0.0
            return round(frame_count / float(frame_rate), 3)
    except Exception:
        return 0.0


@dataclass
class TranscriptBuildResult:
    status: str
    source: str
    segments: list[dict]
    error: str = ""


def _write_segments(transcript_path: Path, segments: list[dict]) -> None:
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(
        json.dumps(segments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_single_segment(text: str, source: str, duration_seconds: float) -> list[dict]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    return [
        {
            "start_sec": 0.0,
            "end_sec": round(max(duration_seconds, 0.0), 3),
            "text": normalized,
            "speaker": "teacher",
        }
    ]


def _parse_session_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone().replace(tzinfo=None)
    except Exception:
        return None


def _transcribe_from_chat_cache(
    session_started_at: str,
    session_ended_at: str,
    duration_seconds: float,
) -> tuple[list[dict], str]:
    started_dt = _parse_session_time(session_started_at)
    ended_dt = _parse_session_time(session_ended_at)
    if started_dt is None or ended_dt is None:
        return [], "chat_cache_time_window_missing"
    if not CHAT_LOG_PATH.exists():
        return [], "chat_cache_log_missing"

    matched: list[tuple[datetime, str]] = []
    try:
        for raw_line in CHAT_LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = CHAT_RECOGNIZE_PATTERN.search(raw_line)
            if not match:
                continue
            text = _normalize_text(match.group("text"))
            if not text:
                continue
            ts = datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S")
            if started_dt <= ts <= ended_dt:
                matched.append((ts, text))
    except Exception as exc:
        return [], f"chat_cache_parse_failed:{exc}"

    if not matched:
        return [], "chat_cache_empty"

    segments: list[dict] = []
    total_duration = max(duration_seconds, 0.0)
    for index, (ts, text) in enumerate(matched):
        start_sec = max(0.0, round((ts - started_dt).total_seconds(), 3))
        if index + 1 < len(matched):
            next_ts = matched[index + 1][0]
            end_sec = max(start_sec, round((next_ts - started_dt).total_seconds(), 3))
        else:
            end_sec = max(start_sec, round(total_duration, 3))
        segments.append(
            {
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": text,
                "speaker": "teacher",
            }
        )
    return segments, ""


def _transcribe_with_azure(audio_path: Path) -> tuple[list[dict], str]:
    azure_key = str(_setting("azure_key", "")).strip()
    if not azure_key:
        return [], "azure_key_missing"

    headers = {
        "Accept": "application/json;text/xml",
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Ocp-Apim-Subscription-Key": azure_key,
    }

    session = requests.Session()
    if not os.environ.get("HTTP_PROXY") and not os.environ.get("http_proxy"):
        session.trust_env = False

    response_text = ""
    try:
        with audio_path.open("rb") as audio_file:
            response = session.post(
                AZURE_STT_URL,
                headers=headers,
                files={"file": audio_file},
                timeout=20,
            )
        response_text = response.text
        if response.status_code >= 400:
            return [], f"azure_http_{response.status_code}"
        payload = json.loads(response_text or "{}")
    except Exception as exc:
        return [], f"azure_request_failed:{exc}"

    display_text = _normalize_text(str(payload.get("DisplayText", "")))
    if not display_text:
        return [], "azure_empty_text"

    return _build_single_segment(display_text, "azure_stt", _audio_duration(audio_path)), ""


def _transcribe_with_vosk(audio_path: Path) -> tuple[list[dict], str]:
    try:
        from voskReco import vosk_reco
    except Exception as exc:
        return [], f"vosk_import_failed:{exc}"

    try:
        text = _normalize_text(vosk_reco.recognize(str(audio_path)))
    except Exception as exc:
        return [], f"vosk_recognize_failed:{exc}"

    if not text:
        return [], "vosk_empty_text"

    return _build_single_segment(text, "vosk_stt", _audio_duration(audio_path)), ""


def build_teacher_transcript(
    audio_path: Path,
    transcript_path: Path,
    session_started_at: str = "",
    session_ended_at: str = "",
) -> TranscriptBuildResult:
    duration_seconds = _audio_duration(audio_path) if audio_path.exists() else 0.0
    if not audio_path.exists():
        segments, error = _transcribe_from_chat_cache(
            session_started_at,
            session_ended_at,
            duration_seconds,
        )
        if segments:
            result = TranscriptBuildResult(
                status="completed",
                source="chat_cache",
                segments=segments,
                error="",
            )
            _write_segments(transcript_path, result.segments)
            return result
        result = TranscriptBuildResult(
            status="unavailable",
            source="unavailable",
            segments=[],
            error=f"audio_not_found; {error}",
        )
        _write_segments(transcript_path, result.segments)
        return result

    use_online = bool(_setting("use_online_recognize", True))
    attempts: list[tuple[str, str]] = []

    sources = ["azure_stt", "vosk_stt"] if use_online else ["vosk_stt", "azure_stt"]
    for source in sources:
        if source == "azure_stt":
            segments, error = _transcribe_with_azure(audio_path)
        else:
            segments, error = _transcribe_with_vosk(audio_path)

        if segments:
            result = TranscriptBuildResult(
                status="completed",
                source=source,
                segments=segments,
                error="",
            )
            _write_segments(transcript_path, result.segments)
            logger.info(
                "teacher_transcript generated: path=%s source=%s segments=%s",
                transcript_path,
                source,
                len(segments),
            )
            return result

        attempts.append((source, error))
        logger.warning(
            "teacher_transcript source unavailable: source=%s error=%s",
            source,
            error,
        )

    segments, cache_error = _transcribe_from_chat_cache(
        session_started_at,
        session_ended_at,
        duration_seconds,
    )
    if segments:
        result = TranscriptBuildResult(
            status="completed",
            source="chat_cache",
            segments=segments,
            error="",
        )
        _write_segments(transcript_path, result.segments)
        logger.info(
            "teacher_transcript generated: path=%s source=%s segments=%s",
            transcript_path,
            result.source,
            len(result.segments),
        )
        return result

    attempts.append(("chat_cache", cache_error))
    result = TranscriptBuildResult(
        status="unavailable",
        source="unavailable",
        segments=[],
        error="; ".join(f"{name}:{error}" for name, error in attempts if error),
    )
    _write_segments(transcript_path, result.segments)
    return result
