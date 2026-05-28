from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

import psutil

try:
    from app_config import settings
except Exception:
    settings = None


def _setting(name: str, default):
    return getattr(settings, name, default) if settings is not None else default


def _pid_file() -> Path:
    return Path(str(_setting("pi_capture_pid_file", "captures/.capture_session.pid"))).resolve()


def _state_file() -> Path:
    return Path(str(_setting("pi_capture_state_file", "captures/.capture_session_state.json"))).resolve()


def _stop_file() -> Path:
    return Path(str(_setting("pi_capture_stop_file", "captures/.capture_session.stop"))).resolve()


def _read_pid() -> int:
    pid_path = _pid_file()
    if not pid_path.exists():
        return 0
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except Exception:
        return 0


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False


def _write_pid(pid: int) -> None:
    path = _pid_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid), encoding="utf-8")


def _clear_pid() -> None:
    path = _pid_file()
    if path.exists():
        path.unlink()


def _write_stop_request(pid: int) -> None:
    path = _stop_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "pid": pid,
                "requested_at": time.time(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _clear_stop_request() -> None:
    path = _stop_file()
    if path.exists():
        path.unlink()


def _write_state(payload: dict) -> None:
    path = _state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_state() -> dict:
    path = _state_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def cmd_start(args) -> int:
    from pi_capture_runtime import CaptureSessionConfig, PiCaptureSession

    existing_pid = _read_pid()
    if _is_pid_running(existing_pid):
        print(f"capture session already running: pid={existing_pid}")
        return 1

    config = CaptureSessionConfig.from_settings(
        classroom_id=args.classroom_id,
        device_id=args.device_id,
        duration_seconds=args.duration,
    )
    session = PiCaptureSession(config)

    _clear_stop_request()
    _write_pid(os.getpid())
    _write_state(
        {
            "pid": os.getpid(),
            "status": "starting",
            "classroom_id": config.classroom_id,
            "device_id": config.device_id,
        }
    )

    def _cleanup():
        _clear_pid()
        _clear_stop_request()

    atexit.register(_cleanup)

    def _handle_signal(sig, frame):
        session.request_stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    def _watch_stop_request() -> None:
        stop_path = _stop_file()
        while not session.stop_event.is_set():
            if stop_path.exists():
                session.request_stop()
                break
            time.sleep(0.25)

    stop_watcher = threading.Thread(
        target=_watch_stop_request,
        name="capture-stop-watcher",
        daemon=True,
    )
    stop_watcher.start()

    try:
        session.start()
        _write_state(
            {
                "pid": os.getpid(),
                "status": "recording",
                **session.status_snapshot(),
            }
        )
        session.run()
    except Exception as exc:
        _write_state(
            {
                "pid": os.getpid(),
                "status": "failed",
                "error": str(exc),
            }
        )
        raise
    finally:
        _write_state(
            {
                "pid": os.getpid(),
                "status": session.metadata.status,
                "metadata_path": str(session.metadata_path),
                "capture_metadata_path": str(session.capture_metadata_path),
                "transcript_path": str(session.teacher_transcript_path),
                "transcript_status": session.metadata.transcript_status,
                "transcript_source": session.metadata.transcript_source,
                "teacher_questions_path": str(session.teacher_questions_path),
                "teacher_question_status": session.metadata.teacher_question_status,
                "teacher_question_count": session.metadata.teacher_question_count,
                "delivery_status": session.metadata.delivery_status,
                "session_ready": session.metadata.session_ready,
                "delivery_path": session.metadata.delivery_path,
                "video_size": session.metadata.video_size,
                "audio_size": session.metadata.audio_size,
                "transcript_size": session.metadata.transcript_size,
                "transcript_count": session.metadata.transcript_count,
                "session_dir": str(session.session_dir),
                "capture_id": session.capture_id,
                "classroom_id": session.config.classroom_id,
                "device_id": session.config.device_id,
            }
        )

    print(json.dumps(session.status_snapshot(), ensure_ascii=False, indent=2))
    return 0


def cmd_stop(_args) -> int:
    pid = _read_pid()
    if not _is_pid_running(pid):
        print("no running capture session")
        return 1
    _write_stop_request(pid)
    if os.name != "nt":
        os.kill(pid, signal.SIGINT)
    print(f"stop requested: pid={pid}")
    return 0


def cmd_status(_args) -> int:
    pid = _read_pid()
    state = _read_state()
    payload = {
        "pid": pid,
        "running": _is_pid_running(pid),
        "state": state,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pi classroom capture mainline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="start a capture session")
    start.add_argument("--classroom-id", default=None)
    start.add_argument("--device-id", default=None)
    start.add_argument("--duration", type=int, default=None)
    start.set_defaults(func=cmd_start)

    stop = subparsers.add_parser("stop", help="stop the running capture session")
    stop.set_defaults(func=cmd_stop)

    status = subparsers.add_parser("status", help="show capture session status")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
