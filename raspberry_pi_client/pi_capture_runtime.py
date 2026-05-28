from __future__ import annotations

import json
import logging
import shutil
import socket
import threading
import time
import uuid
import wave
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import pyaudio

try:
    from app_config import settings
except Exception:
    settings = None

from pi_transcript_delivery import build_teacher_transcript
from pi_teacher_questions import build_teacher_questions
from video_standardizer import standardize_video


logger = logging.getLogger("pi_capture_runtime")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
    )


def _setting(name: str, default):
    return getattr(settings, name, default) if settings is not None else default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _copy_tree(src: Path, dst: Path) -> None:
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _copy_tree(item, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


@dataclass
class CaptureMetadata:
    capture_id: str
    classroom_id: str
    device_id: str
    source_host: str
    started_at: str
    ended_at: str
    duration_seconds: float
    local_video_path: str
    local_audio_path: str
    status: str
    delivery_status: str = "recording"
    session_ready: bool = False
    delivery_mode: str = ""
    delivery_path: str = ""
    transcript_path: str = ""
    transcript_status: str = "unavailable"
    transcript_source: str = "unavailable"
    video_size: int = 0
    audio_size: int = 0
    transcript_size: int = 0
    transcript_count: int = 0
    transcript_error: str = ""
    teacher_question_status: str = "unavailable"
    teacher_question_count: int = 0
    teacher_question_file: str = "teacher_questions.json"
    teacher_question_error: str = ""
    error: str = ""


@dataclass
class CaptureSessionConfig:
    classroom_id: str
    device_id: str
    device_name: str
    source_host: str
    capture_root: Path
    delivery_mode: str
    delivery_root: Path
    camera_id: int
    audio_device_index: int
    video_fps: int
    frame_width: int
    frame_height: int
    duration_seconds: Optional[int] = None
    audio_rate: int = 16000
    audio_channels: int = 1
    audio_chunk: int = 1024

    @classmethod
    def from_settings(
        cls,
        classroom_id: Optional[str] = None,
        device_id: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> "CaptureSessionConfig":
        source_host = socket.gethostname()
        resolved_classroom = classroom_id or str(
            _setting("pi_default_classroom_id", "classroom-default")
        )
        configured_device = str(_setting("pi_device_id", "")).strip()
        resolved_device = device_id or configured_device or source_host
        configured_device_name = str(_setting("pi_device_name", "")).strip()
        resolved_device_name = configured_device_name or f"Raspberry Pi - {resolved_device}"
        return cls(
            classroom_id=resolved_classroom,
            device_id=resolved_device,
            device_name=resolved_device_name,
            source_host=source_host,
            capture_root=Path(str(_setting("pi_capture_root", "captures"))),
            delivery_mode=str(_setting("pi_capture_delivery_mode", "shared_dir")),
            delivery_root=Path(str(_setting("pi_local_delivery_root", "captures_local_delivery"))),
            camera_id=int(_setting("pi_capture_camera_id", 0)),
            audio_device_index=int(_setting("pi_capture_audio_device_index", -1)),
            video_fps=max(1, int(_setting("pi_capture_video_fps", 25))),
            frame_width=max(320, int(_setting("pi_capture_frame_width", 1280))),
            frame_height=max(240, int(_setting("pi_capture_frame_height", 720))),
            duration_seconds=duration_seconds,
        )


class PiCaptureSession:
    def __init__(self, config: CaptureSessionConfig) -> None:
        self.config = config
        self.capture_id = uuid.uuid4().hex
        self.session_id = self.capture_id
        self.started_monotonic = 0.0
        self.stop_event = threading.Event()
        self.capture_error = ""

        self.video_capture = None
        self.video_writer = None
        self.audio_interface = None
        self.audio_stream = None
        self.audio_wave = None
        self.video_thread: Optional[threading.Thread] = None
        self.audio_thread: Optional[threading.Thread] = None

        session_date = datetime.now().strftime("%Y-%m-%d")
        self.session_dir = (
            self.config.capture_root
            / self.config.classroom_id
            / session_date
            / self.session_id
        ).resolve()
        self.video_path = self.session_dir / "video.mp4"
        self.standardized_video_path = self.session_dir / "standardized_video.mp4"
        self.audio_path = self.session_dir / "audio.wav"
        self.metadata_path = self.session_dir / "metadata.json"
        self.capture_metadata_path = self.session_dir / "capture_metadata.json"
        self.teacher_transcript_path = self.session_dir / "teacher_transcript.json"
        self.teacher_questions_path = self.session_dir / "teacher_questions.json"
        self.video_metadata = {
            "raw_video_path": str(self.video_path),
            "standardized_video_path": str(self.standardized_video_path),
            "format": "unknown",
            "codec": "unknown",
            "audio_codec": "unknown",
            "browser_compatible": False,
            "transcode_status": "unknown",
            "transcode_error": "",
        }

        self.metadata = CaptureMetadata(
            capture_id=self.capture_id,
            classroom_id=self.config.classroom_id,
            device_id=self.config.device_id,
            source_host=self.config.source_host,
            started_at="",
            ended_at="",
            duration_seconds=0.0,
            local_video_path=str(self.video_path),
            local_audio_path=str(self.audio_path),
            status="initialized",
            transcript_path=str(self.teacher_transcript_path),
        )

    def _capture_metadata_payload(self) -> dict:
        return {
            "capture": {
                "device_id": self.config.device_id,
                "device_name": self.config.device_name,
                "classroom_id": self.config.classroom_id,
                "captured_at": self.metadata.started_at or _now_iso(),
                "video_path": str(self.video_path),
                "standardized_video_path": str(self.standardized_video_path),
                "keyframe_dir": str(self.session_dir / "keyframes"),
            },
            "video": self.video_metadata,
        }

    def start(self) -> None:
        logger.info(
            "Starting capture session: classroom_id=%s device_id=%s camera_id=%s delivery_mode=%s",
            self.config.classroom_id,
            self.config.device_id,
            self.config.camera_id,
            self.config.delivery_mode,
        )
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.metadata.started_at = _now_iso()
        self.metadata.status = "recording"
        _write_json(self.metadata_path, asdict(self.metadata))
        self._write_capture_metadata()

        self._open_video()
        self._open_audio()

        self.started_monotonic = time.monotonic()
        self.video_thread = threading.Thread(
            target=self._video_loop,
            name="capture-video",
            daemon=True,
        )
        self.audio_thread = threading.Thread(
            target=self._audio_loop,
            name="capture-audio",
            daemon=True,
        )
        self.video_thread.start()
        self.audio_thread.start()

    def run(self) -> None:
        try:
            while not self.stop_event.is_set():
                if (
                    self.config.duration_seconds is not None
                    and self.started_monotonic > 0
                    and (time.monotonic() - self.started_monotonic) >= self.config.duration_seconds
                ):
                    logger.info("Capture duration reached, stopping session")
                    self.stop_event.set()
                    break
                time.sleep(0.5)
        finally:
            self.stop()

    def request_stop(self) -> None:
        self.stop_event.set()

    def stop(self) -> None:
        self.stop_event.set()

        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=5)
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=5)

        self._close_resources()

        ended_at = _now_iso()
        duration_seconds = 0.0
        if self.started_monotonic > 0:
            duration_seconds = max(0.0, time.monotonic() - self.started_monotonic)

        self.metadata.ended_at = ended_at
        self.metadata.duration_seconds = round(duration_seconds, 3)
        self.metadata.status = "failed" if self.capture_error else "completed"
        self.metadata.error = self.capture_error
        self.metadata.delivery_status = "failed" if self.capture_error else "finalizing"
        self.metadata.session_ready = False
        self._standardize_video()
        self._generate_transcript()
        self._refresh_file_integrity()
        self._write_metadata()
        self._write_capture_metadata()

        delivery_dir: Optional[Path] = None
        try:
            delivery_dir = self._build_delivery_dir()
            self.metadata.delivery_mode = self.config.delivery_mode
            self.metadata.delivery_path = str(delivery_dir)
            self.metadata.delivery_status = "copying"
            self.metadata.session_ready = False
            self._write_metadata()

            self._deliver_capture(delivery_dir)

            local_complete = self._session_files_complete(self.session_dir)
            delivery_complete = self._session_files_complete(delivery_dir)
            ready = (
                self.metadata.status == "completed"
                and local_complete
                and delivery_complete
            )
            self.metadata.delivery_status = "ready" if ready else "failed"
            self.metadata.session_ready = ready
            if not ready and not self.metadata.error:
                reasons = []
                if not local_complete:
                    reasons.append("local_session_incomplete")
                if not delivery_complete:
                    reasons.append("delivery_session_incomplete")
                self.metadata.error = ",".join(reasons) or "session_not_ready"
        except Exception as exc:
            self.metadata.status = "failed"
            self.metadata.delivery_status = "failed"
            self.metadata.session_ready = False
            self.metadata.error = f"delivery_failed: {exc}"
            logger.exception("Capture delivery failed: %s", exc)

        self._refresh_file_integrity()
        self._write_metadata(delivery_dir)
        self._write_capture_metadata(delivery_dir)
        logger.info(
            "Capture session finished: capture_id=%s status=%s metadata=%s",
            self.capture_id,
            self.metadata.status,
            self.metadata_path,
        )

    def status_snapshot(self) -> dict:
        return {
            "capture_id": self.capture_id,
            "classroom_id": self.config.classroom_id,
            "device_id": self.config.device_id,
            "session_dir": str(self.session_dir),
            "metadata_path": str(self.metadata_path),
            "capture_metadata_path": str(self.capture_metadata_path),
            "standardized_video_path": str(self.standardized_video_path),
            "transcript_path": str(self.teacher_transcript_path),
            "teacher_questions_path": str(self.teacher_questions_path),
            "delivery_status": self.metadata.delivery_status,
            "session_ready": self.metadata.session_ready,
            "delivery_path": self.metadata.delivery_path,
            "transcript_count": self.metadata.transcript_count,
            "teacher_question_count": self.metadata.teacher_question_count,
            "status": self.metadata.status,
        }

    def _standardize_video(self) -> None:
        try:
            result = standardize_video(
                self.video_path,
                self.standardized_video_path,
                audio_path=self.audio_path,
            )
            self.video_metadata = result.as_metadata()
            if result.transcode_status == "failed":
                logger.warning("standardized_video generation failed: %s", result.transcode_error)
            else:
                logger.info(
                    "standardized_video generated: path=%s status=%s",
                    self.standardized_video_path,
                    result.transcode_status,
                )
        except Exception as exc:
            self.video_metadata = {
                "raw_video_path": str(self.video_path),
                "standardized_video_path": str(self.standardized_video_path),
                "format": "unknown",
                "codec": "unknown",
                "audio_codec": "unknown",
                "browser_compatible": False,
                "transcode_status": "failed",
                "transcode_error": str(exc),
            }
            logger.exception("standardized_video generation failed: %s", exc)

    def _generate_transcript(self) -> None:
        try:
            result = build_teacher_transcript(
                self.audio_path,
                self.teacher_transcript_path,
                session_started_at=self.metadata.started_at,
                session_ended_at=self.metadata.ended_at,
            )
        except Exception as exc:
            logger.exception("teacher_transcript generation failed: %s", exc)
            self.metadata.transcript_status = "unavailable"
            self.metadata.transcript_source = "unavailable"
            self.metadata.transcript_error = str(exc)
            self._generate_teacher_questions()
            return

        self.metadata.transcript_status = result.status
        self.metadata.transcript_source = result.source
        self.metadata.transcript_error = result.error

        self._generate_teacher_questions()

    def _generate_teacher_questions(self) -> None:
        try:
            result = build_teacher_questions(
                self.teacher_transcript_path,
                self.teacher_questions_path,
                capture_id=self.capture_id,
                classroom_id=self.config.classroom_id,
                transcript_status=self.metadata.transcript_status,
                transcript_source=self.metadata.transcript_source,
            )
        except Exception as exc:
            logger.exception("teacher_questions generation failed: %s", exc)
            self.metadata.teacher_question_status = "unavailable"
            self.metadata.teacher_question_count = 0
            self.metadata.teacher_question_file = "teacher_questions.json"
            self.metadata.teacher_question_error = str(exc)
            return

        self.metadata.teacher_question_status = result.status
        self.metadata.teacher_question_count = result.question_count
        self.metadata.teacher_question_file = "teacher_questions.json"
        self.metadata.teacher_question_error = result.error

    def _open_video(self) -> None:
        capture = cv2.VideoCapture(self.config.camera_id)
        if not capture.isOpened():
            raise RuntimeError(f"failed_to_open_video_device:{self.config.camera_id}")

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
        capture.set(cv2.CAP_PROP_FPS, self.config.video_fps)

        actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.config.frame_width
        actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.config.frame_height
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(self.video_path),
            fourcc,
            float(self.config.video_fps),
            (actual_width, actual_height),
        )
        if not writer.isOpened():
            capture.release()
            raise RuntimeError("failed_to_open_video_writer")

        self.video_capture = capture
        self.video_writer = writer

    def _open_audio(self) -> None:
        audio = pyaudio.PyAudio()
        open_kwargs = {
            "format": pyaudio.paInt16,
            "channels": self.config.audio_channels,
            "rate": self.config.audio_rate,
            "frames_per_buffer": self.config.audio_chunk,
            "input": True,
        }
        if self.config.audio_device_index >= 0:
            open_kwargs["input_device_index"] = self.config.audio_device_index

        stream = audio.open(**open_kwargs)
        wave_file = wave.open(str(self.audio_path), "wb")
        wave_file.setnchannels(self.config.audio_channels)
        wave_file.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wave_file.setframerate(self.config.audio_rate)

        self.audio_interface = audio
        self.audio_stream = stream
        self.audio_wave = wave_file

    def _video_loop(self) -> None:
        frame_interval = 1.0 / max(1, self.config.video_fps)
        while not self.stop_event.is_set():
            loop_started = time.monotonic()
            ok, frame = self.video_capture.read()
            if not ok or frame is None:
                self.capture_error = "video_frame_read_failed"
                self.stop_event.set()
                logger.error("Video frame read failed")
                break
            self.video_writer.write(frame)
            elapsed = time.monotonic() - loop_started
            sleep_seconds = frame_interval - elapsed
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    def _audio_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                data = self.audio_stream.read(
                    self.config.audio_chunk,
                    exception_on_overflow=False,
                )
            except Exception as exc:
                self.capture_error = f"audio_read_failed:{exc}"
                self.stop_event.set()
                logger.exception("Audio read failed: %s", exc)
                break
            self.audio_wave.writeframes(data)

    def _write_metadata(self, delivery_dir: Optional[Path] = None) -> None:
        _write_json(self.metadata_path, asdict(self.metadata))
        if delivery_dir is not None and delivery_dir.exists():
            _write_json(delivery_dir / "metadata.json", asdict(self.metadata))

    def _write_capture_metadata(self, delivery_dir: Optional[Path] = None) -> None:
        payload = self._capture_metadata_payload()
        _write_json(self.capture_metadata_path, payload)
        if delivery_dir is not None and delivery_dir.exists():
            _write_json(delivery_dir / "capture_metadata.json", payload)

    def _transcript_count(self, transcript_path: Path) -> int:
        if not transcript_path.exists():
            return 0
        try:
            payload = json.loads(transcript_path.read_text(encoding="utf-8"))
        except Exception:
            return 0
        return len(payload) if isinstance(payload, list) else 0

    def _refresh_file_integrity(self) -> None:
        self.metadata.video_size = self.video_path.stat().st_size if self.video_path.exists() else 0
        self.metadata.audio_size = self.audio_path.stat().st_size if self.audio_path.exists() else 0
        self.metadata.transcript_size = (
            self.teacher_transcript_path.stat().st_size
            if self.teacher_transcript_path.exists()
            else 0
        )
        self.metadata.transcript_count = self._transcript_count(self.teacher_transcript_path)

    def _session_files_complete(self, base_dir: Path) -> bool:
        required_files = [
            base_dir / "video.mp4",
            base_dir / "standardized_video.mp4",
            base_dir / "audio.wav",
            base_dir / "metadata.json",
            base_dir / "capture_metadata.json",
            base_dir / "teacher_transcript.json",
            base_dir / "teacher_questions.json",
        ]
        if not all(path.exists() for path in required_files):
            return False
        return all(path.stat().st_size > 0 for path in required_files)

    def _build_delivery_dir(self) -> Path:
        if self.config.delivery_mode != "shared_dir":
            raise RuntimeError(f"unsupported_delivery_mode:{self.config.delivery_mode}")

        return (
            self.config.delivery_root
            / self.config.classroom_id
            / self.session_dir.parent.name
            / self.session_id
        ).resolve()

    def _deliver_capture(self, delivery_dir: Path) -> str:
        delivery_dir.mkdir(parents=True, exist_ok=True)
        _copy_tree(self.session_dir, delivery_dir)
        logger.info("Capture delivered to shared dir: %s", delivery_dir)
        return str(delivery_dir)

    def _close_resources(self) -> None:
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
        if self.audio_stream is not None:
            try:
                self.audio_stream.stop_stream()
            except Exception:
                pass
            self.audio_stream.close()
            self.audio_stream = None
        if self.audio_wave is not None:
            self.audio_wave.close()
            self.audio_wave = None
        if self.audio_interface is not None:
            self.audio_interface.terminate()
            self.audio_interface = None
