from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_DIR = BASE_DIR / "scripts" / "sample_keyframes"
DEFAULT_SERVER = "http://127.0.0.1:8000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="测试本地计算机端关键帧接收与处理接口")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="本地接收服务地址")
    parser.add_argument("--sample-dir", default=str(DEFAULT_SAMPLE_DIR), help="测试图片目录")
    parser.add_argument("--window-id", default=f"test_window_{int(time.time())}", help="测试窗口 ID")
    parser.add_argument("--device-id", default="pi-test-001", help="测试设备 ID")
    parser.add_argument("--classroom-id", default="room-test-001", help="测试教室 ID")
    parser.add_argument("--timestamp", default=datetime.now().isoformat(timespec="seconds"), help="窗口时间戳")
    parser.add_argument("--skip-health", action="store_true", help="跳过健康检查")
    parser.add_argument("--generate-samples", action="store_true", help="若样例目录为空，则自动生成测试图片")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sample_dir = Path(args.sample_dir).resolve()

    if args.generate_samples:
        ensure_sample_images(sample_dir)

    image_paths = collect_images(sample_dir)
    if not image_paths:
        print(f"[ERROR] 测试图片不存在，请准备 JPEG 文件到目录: {sample_dir}")
        print("[TIP] 可添加参数 --generate-samples 自动生成测试图片")
        return 1

    print(f"[INFO] 使用服务地址: {args.server}")
    print(f"[INFO] 使用测试图片目录: {sample_dir}")
    print(f"[INFO] 测试图片数量: {len(image_paths)}")

    if not args.skip_health:
        if not test_health(args.server):
            return 1

    success = post_keyframes(
        server=args.server,
        image_paths=image_paths,
        window_id=args.window_id,
        device_id=args.device_id,
        classroom_id=args.classroom_id,
        timestamp=args.timestamp,
    )
    return 0 if success else 1


def test_health(server: str) -> bool:
    health_url = f"{server.rstrip('/')}/health"
    print(f"[INFO] 检查健康接口: {health_url}")
    try:
        response = requests.get(health_url, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] 健康检查失败: {exc}")
        return False

    print("[INFO] 健康检查成功")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    return True


def post_keyframes(
    *,
    server: str,
    image_paths: list[Path],
    window_id: str,
    device_id: str,
    classroom_id: str,
    timestamp: str,
) -> bool:
    post_url = f"{server.rstrip('/')}/api/keyframes"
    frame_timestamps = build_frame_timestamps(timestamp, len(image_paths))
    metadata = {
        "source": "local_test_script",
        "note": "用于验证本地接收、YOLO 推理与统计输出链路",
        "analysis_id": f"analysis_{window_id}",
        "video_id": f"video_{window_id}",
        "source_kind": "captured_video",
        "source_path": str(image_paths[0].parent),
        "source_host": "raspberrypi-01",
        "recorded_at": timestamp,
        "teacher_transcript_segments": [
            {"start_sec": 2, "end_sec": 6, "text": "谁来回答一下这个问题？"},
            {"start_sec": 8, "end_sec": 14, "text": "我们继续讲解下一部分内容。"},
        ],
        "timeline": {
            "window_size_seconds": 20,
            "heat_curve": [0.18],
        },
    }

    data = {
        "window_id": window_id,
        "timestamp": timestamp,
        "device_id": device_id,
        "classroom_id": classroom_id,
        "frame_timestamps": json.dumps(frame_timestamps, ensure_ascii=False),
        "metadata_json": json.dumps(metadata, ensure_ascii=False),
    }

    files = []
    file_handles = []
    try:
        for image_path in image_paths:
            file_handle = image_path.open("rb")
            file_handles.append(file_handle)
            files.append(("images", (image_path.name, file_handle, "image/jpeg")))

        print(f"[INFO] 开始上传关键帧: {post_url}")
        response = requests.post(post_url, data=data, files=files, timeout=120)
        response.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] 关键帧上传失败: {exc}")
        return False
    finally:
        for file_handle in file_handles:
            file_handle.close()

    print("[INFO] 关键帧上传成功")
    try:
        payload = response.json()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        print(response.text)
        return False

    result_path = payload.get("result_path")
    if result_path:
        print(f"[INFO] 结果 JSON 路径: {result_path}")
    return True


def collect_images(sample_dir: Path) -> list[Path]:
    if not sample_dir.exists():
        return []
    image_paths = sorted(
        [
            path
            for path in sample_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
        ]
    )
    return image_paths


def build_frame_timestamps(base_timestamp: str, image_count: int) -> list[str]:
    try:
        start = datetime.fromisoformat(base_timestamp)
    except ValueError:
        start = datetime.now()
    return [(start + timedelta(seconds=index * 2)).isoformat(timespec="seconds") for index in range(image_count)]


def ensure_sample_images(sample_dir: Path) -> None:
    sample_dir.mkdir(parents=True, exist_ok=True)
    existing = collect_images(sample_dir)
    if existing:
        print(f"[INFO] 样例目录已有图片，跳过生成: {sample_dir}")
        return

    try:
        import cv2
        import numpy as np
    except Exception as exc:
        print(f"[ERROR] 自动生成测试图片失败，缺少依赖: {exc}")
        return

    print(f"[INFO] 自动生成测试图片到: {sample_dir}")
    for index in range(3):
        canvas = np.full((720, 1280, 3), 255, dtype=np.uint8)
        cv2.putText(canvas, f"Local Test Frame {index + 1}", (80, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 0), 3)
        cv2.rectangle(canvas, (180, 220), (380, 620), (0, 128, 255), 3)
        cv2.rectangle(canvas, (760, 180), (980, 650), (0, 200, 0), 3)
        cv2.putText(canvas, "student_a", (185, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 128, 255), 2)
        cv2.putText(canvas, "student_b", (765, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
        cv2.imwrite(str(sample_dir / f"sample_{index + 1:03d}.jpg"), canvas)


if __name__ == "__main__":
    sys.exit(main())
