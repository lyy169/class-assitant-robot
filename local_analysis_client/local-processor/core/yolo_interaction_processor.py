from __future__ import annotations

import json
import logging
import socket
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from ultralytics import YOLO


LOGGER = logging.getLogger("yolo_interaction")
CLOUD_PUSH_RETRY_DELAYS = (1, 2, 4)
RESULT_SCHEMA_VERSION = "v1.1"
REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_RESULT_ROOT_FIELDS = (
    "schema_version",
    "analysis_id",
    "classroom_id",
    "video_id",
    "source",
    "time",
    "summary",
    "teacher",
    "students",
    "timeline",
)
REQUIRED_SUMMARY_FIELDS = (
    "feedback_score",
    "attention_score",
    "response_score",
    "teacher_question_count",
    "avg_attention_ratio",
    "response_success_rate",
    "summary_text",
)


@dataclass
class ProcessorConfig:
    """处理器配置。所有字段默认由 config.yaml 注入。"""

    config_path: Path
    base_dir: Path
    received_keyframes_dir: Path
    output_dir: Path
    source_host: str
    use_merged_model: bool
    merged_model_path: Path | None
    hand_model_path: Path | None
    standing_model_path: Path | None
    imgsz: int
    conf: float
    hand_conf: float
    standing_conf: float
    iou: float
    max_det: int
    region_rows: int
    region_cols: int
    window_seconds: int
    event_gap_seconds: float
    hand_class_names: tuple[str, ...]
    standing_class_names: tuple[str, ...]
    save_debug_json: bool
    cloud_push_enabled: bool
    cloud_push_url: str | None
    cloud_push_timeout: int
    cloud_push_headers: dict[str, str]


@dataclass
class FrameRecord:
    index: int
    file_path: str
    timestamp: float
    file_name: str


@dataclass
class DetectionRecord:
    frame_index: int
    timestamp: float
    action: str
    class_name: str
    confidence: float
    bbox_xyxy: list[float]
    center: list[float]
    region_id: str
    region_index: int
    source_file: str


@dataclass
class RegionStats:
    region_id: str
    row: int
    col: int
    hand_raising_count: int = 0
    standing_count: int = 0
    total_events: int = 0
    hand_frames: int = 0
    standing_frames: int = 0


def configure_logging(config_path: str | Path | None = None) -> None:
    """按配置初始化日志。"""
    raw = load_raw_config(config_path)
    log_cfg = raw.get("logging", {})
    level_name = str(log_cfg.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = log_cfg.get("format", "%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    logging.basicConfig(level=level, format=log_format, force=True)


def load_raw_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """读取原始 YAML 配置。"""
    resolved_path = resolve_config_path(config_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {resolved_path}")
    with resolved_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"配置文件格式错误，根节点必须为字典: {resolved_path}")
    return data


def resolve_config_path(config_path: str | Path | None = None) -> Path:
    """解析配置文件路径。"""
    if config_path is not None:
        return Path(config_path).resolve()

    default_candidates = (
        REPO_ROOT / "config.yaml",
        REPO_ROOT / "configs" / "local-processor.yaml",
    )
    for candidate in default_candidates:
        if candidate.exists():
            return candidate.resolve()

    return (REPO_ROOT / "config.yaml").resolve()


def load_processor_config(config_path: str | Path | None = None) -> ProcessorConfig:
    """从 config.yaml 构造处理器配置。"""
    raw = load_raw_config(config_path)
    config_file = resolve_config_path(config_path)
    repo_dir = config_file.parent

    paths_cfg = raw.get("paths", {})
    models_cfg = raw.get("models", {})
    inference_cfg = raw.get("inference", {})
    statistics_cfg = raw.get("statistics", {})
    cloud_cfg = raw.get("cloud", {})
    runtime_cfg = raw.get("runtime", {})

    base_dir = (repo_dir / paths_cfg.get("base_dir", ".")).resolve()
    received_keyframes_dir = (base_dir / paths_cfg.get("received_keyframes_dir", "received_keyframes")).resolve()
    output_dir = (base_dir / paths_cfg.get("processed_results_dir", "processed_results")).resolve()
    source_host = str(runtime_cfg.get("source_host") or socket.gethostname())

    merged_model_path = models_cfg.get("merged_model_path")
    hand_model_path = models_cfg.get("hand_model_path")
    standing_model_path = models_cfg.get("standing_model_path")
    cloud_enabled = cloud_cfg.get("enabled")
    if cloud_enabled is None:
        cloud_enabled = cloud_cfg.get("push_enabled", False)

    cloud_timeout = cloud_cfg.get("timeout")
    if cloud_timeout is None:
        cloud_timeout = cloud_cfg.get("timeout_seconds", 10)

    raw_cloud_headers = cloud_cfg.get("headers", {}) or {}
    if not isinstance(raw_cloud_headers, dict):
        raise ValueError("cloud.headers 必须为字典类型")

    cloud_push_url = cloud_cfg.get("push_url")
    cloud_push_url = str(cloud_push_url).strip() if cloud_push_url else None

    return ProcessorConfig(
        config_path=config_file,
        base_dir=base_dir,
        received_keyframes_dir=received_keyframes_dir,
        output_dir=output_dir,
        source_host=source_host,
        use_merged_model=bool(models_cfg.get("use_merged_model", True)),
        merged_model_path=(base_dir / merged_model_path).resolve() if merged_model_path else None,
        hand_model_path=(base_dir / hand_model_path).resolve() if hand_model_path else None,
        standing_model_path=(base_dir / standing_model_path).resolve() if standing_model_path else None,
        imgsz=int(inference_cfg.get("imgsz", 640)),
        conf=float(inference_cfg.get("conf", 0.35)),
        hand_conf=float(inference_cfg.get("hand_conf", 0.35)),
        standing_conf=float(inference_cfg.get("standing_conf", 0.35)),
        iou=float(inference_cfg.get("iou", 0.45)),
        max_det=int(inference_cfg.get("max_det", 100)),
        region_rows=int(statistics_cfg.get("region_rows", 3)),
        region_cols=int(statistics_cfg.get("region_cols", 3)),
        window_seconds=int(statistics_cfg.get("window_seconds", 20)),
        event_gap_seconds=float(statistics_cfg.get("event_gap_seconds", 2.0)),
        hand_class_names=tuple(models_cfg.get("hand_class_names", ["hand-raising"])),
        standing_class_names=tuple(models_cfg.get("standing_class_names", ["standing"])),
        save_debug_json=bool(statistics_cfg.get("save_debug_json", True)),
        cloud_push_enabled=bool(cloud_enabled),
        cloud_push_url=cloud_push_url,
        cloud_push_timeout=int(cloud_timeout),
        cloud_push_headers={str(key): str(value) for key, value in raw_cloud_headers.items()},
    )


class YoloInteractionProcessor:
    """YOLO 互动处理器。

    目标：
    1. 加载单个合并后的双类模型。
    2. 对一个 20 秒窗口内的关键帧执行检测。
    3. 基于 3x3 区域完成 20 秒窗口统计，并输出结构化 JSON。
    """

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.config.received_keyframes_dir.mkdir(parents=True, exist_ok=True)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self._merged_model: YOLO | None = None
        self._hand_model: YOLO | None = None
        self._standing_model: YOLO | None = None
        self._models_loaded = False

    def process_window(
        self,
        *,
        window_id: str,
        frame_paths: list[str | Path],
        window_timestamp: str | float | int | None = None,
        frame_timestamps: list[str | float | int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """处理一个窗口的全部关键帧。"""
        if not frame_paths:
            raise ValueError("frame_paths 不能为空")

        self._ensure_models_loaded()
        metadata = metadata or {}
        frames = self._build_frame_records(frame_paths, window_timestamp, frame_timestamps)
        window_start_ts, window_end_ts = self._resolve_window_bounds(frames, window_timestamp)
        frames = self._filter_frames_by_window(frames, window_start_ts, window_end_ts)
        if not frames:
            raise ValueError("20秒窗口内没有可处理的关键帧")
        image_paths = [frame.file_path for frame in frames]

        LOGGER.info(
            "开始处理窗口: window_id=%s frame_count=%s use_merged_model=%s",
            window_id,
            len(frames),
            self.config.use_merged_model,
        )

        try:
            detections = self._run_inference(frames, image_paths)
            result = self._aggregate(
                window_id=window_id,
                frames=frames,
                detections=detections,
                metadata=metadata,
                window_start_ts=window_start_ts,
                window_end_ts=window_end_ts,
            )
        except Exception:
            LOGGER.exception("窗口处理失败: window_id=%s", window_id)
            raise

        output_path = self.config.output_dir / f"{window_id}.json"
        validation_report = validate_result_payload(result)
        if not validation_report["is_valid"]:
            raise ValueError(
                "结果结构校验失败: "
                f"missing_root={validation_report['missing_root_fields']} "
                f"missing_summary={validation_report['missing_summary_fields']}"
            )
        if self.config.save_debug_json:
            self._write_result_json(output_path, result)

        self._push_to_cloud(result, window_id)

        if self.config.save_debug_json:
            self._write_result_json(output_path, result)
        return result

    def _ensure_models_loaded(self) -> None:
        """模型只加载一次，后续复用。"""
        if self._models_loaded:
            return

        if self.config.use_merged_model:
            if not self.config.merged_model_path:
                raise ValueError("当前配置要求使用合并模型，但 merged_model_path 未配置")
            if not self.config.merged_model_path.exists():
                raise FileNotFoundError(f"合并模型不存在: {self.config.merged_model_path}")
            self._merged_model = YOLO(str(self.config.merged_model_path))
            LOGGER.info("已加载合并模型: %s", self.config.merged_model_path)
        else:
            if not self.config.hand_model_path or not self.config.hand_model_path.exists():
                raise FileNotFoundError(f"举手模型不存在: {self.config.hand_model_path}")
            if not self.config.standing_model_path or not self.config.standing_model_path.exists():
                raise FileNotFoundError(f"站立模型不存在: {self.config.standing_model_path}")
            self._hand_model = YOLO(str(self.config.hand_model_path))
            self._standing_model = YOLO(str(self.config.standing_model_path))
            LOGGER.info("已加载举手模型: %s", self.config.hand_model_path)
            LOGGER.info("已加载站立模型: %s", self.config.standing_model_path)

        self._models_loaded = True

    def _build_frame_records(
        self,
        frame_paths: list[str | Path],
        window_timestamp: str | float | int | None,
        frame_timestamps: list[str | float | int] | None,
    ) -> list[FrameRecord]:
        """构造帧记录，并按时间排序。"""
        base_ts = self._to_unix_timestamp(window_timestamp) or datetime.now().timestamp()
        parsed_frame_timestamps = frame_timestamps or []
        frames: list[FrameRecord] = []

        for index, path_value in enumerate(frame_paths):
            path = Path(path_value)
            frame_ts = self._to_unix_timestamp(parsed_frame_timestamps[index]) if index < len(parsed_frame_timestamps) else None
            timestamp = frame_ts if frame_ts is not None else base_ts + index
            frames.append(
                FrameRecord(
                    index=index,
                    file_path=str(path),
                    timestamp=timestamp,
                    file_name=path.name,
                )
            )

        frames.sort(key=lambda item: item.timestamp)
        return frames

    def _resolve_window_bounds(
        self,
        frames: list[FrameRecord],
        window_timestamp: str | float | int | None,
    ) -> tuple[float, float]:
        """解析窗口起止时间，严格限制为配置中的窗口长度。"""
        fallback_start = min((frame.timestamp for frame in frames), default=datetime.now().timestamp())
        window_start_ts = self._to_unix_timestamp(window_timestamp)
        if window_start_ts is None:
            window_start_ts = fallback_start
        window_end_ts = window_start_ts + float(self.config.window_seconds)
        return window_start_ts, window_end_ts

    def _filter_frames_by_window(
        self,
        frames: list[FrameRecord],
        window_start_ts: float,
        window_end_ts: float,
    ) -> list[FrameRecord]:
        """仅保留 20 秒统计窗口内的关键帧。"""
        filtered_frames = [frame for frame in frames if window_start_ts <= frame.timestamp < window_end_ts]
        dropped_count = len(frames) - len(filtered_frames)
        if dropped_count > 0:
            LOGGER.warning(
                "检测到超出统计窗口的关键帧，已忽略: dropped_count=%s window_start=%s window_end=%s",
                dropped_count,
                self._format_timestamp(window_start_ts),
                self._format_timestamp(window_end_ts),
            )
        return filtered_frames

    def _run_inference(self, frames: list[FrameRecord], image_paths: list[str]) -> list[DetectionRecord]:
        """执行推理。

        默认走合并后的双类模型。
        """
        detections: list[DetectionRecord] = []

        if self.config.use_merged_model:
            assert self._merged_model is not None
            LOGGER.info("使用合并模型进行推理: image_count=%s", len(image_paths))
            results = self._predict(self._merged_model, image_paths, self.config.conf)
            detections.extend(self._extract_detections(frames, results, self._merged_model.names))
        else:
            assert self._hand_model is not None
            assert self._standing_model is not None
            LOGGER.info("使用双模型兼容模式进行推理: image_count=%s", len(image_paths))
            hand_results = self._predict(self._hand_model, image_paths, self.config.hand_conf)
            standing_results = self._predict(self._standing_model, image_paths, self.config.standing_conf)
            detections.extend(self._extract_detections(frames, hand_results, self._hand_model.names))
            detections.extend(self._extract_detections(frames, standing_results, self._standing_model.names))

        LOGGER.info("推理完成: detection_count=%s", len(detections))
        return detections

    def _predict(self, model: YOLO, image_paths: list[str], conf: float) -> list[Any]:
        """执行一次 YOLO 预测。"""
        LOGGER.info("开始模型预测: model=%s conf=%.2f imgsz=%s", model.ckpt_path, conf, self.config.imgsz)
        return model.predict(
            source=image_paths,
            conf=conf,
            iou=self.config.iou,
            imgsz=self.config.imgsz,
            max_det=self.config.max_det,
            verbose=False,
            save=False,
            stream=False,
        )

    def _extract_detections(
        self,
        frames: list[FrameRecord],
        results: list[Any],
        model_names: dict[int, str],
    ) -> list[DetectionRecord]:
        """将 Ultralytics 结果转换成统一检测记录。"""
        detections: list[DetectionRecord] = []

        for frame, result in zip(frames, results):
            boxes = getattr(result, "boxes", None)
            if boxes is None or boxes.cls is None or len(boxes) == 0:
                LOGGER.debug("当前帧无检测结果: %s", frame.file_name)
                continue

            orig_shape = getattr(result, "orig_shape", None)
            if not orig_shape:
                LOGGER.warning("当前帧缺少图像尺寸信息，已跳过: %s", frame.file_name)
                continue

            image_h, image_w = orig_shape[:2]
            xyxy_list = boxes.xyxy.tolist()
            cls_list = [int(cls_id) for cls_id in boxes.cls.tolist()]
            conf_list = boxes.conf.tolist() if boxes.conf is not None else [0.0] * len(cls_list)

            for bbox_xyxy, cls_id, confidence in zip(xyxy_list, cls_list, conf_list):
                class_name = model_names.get(cls_id, str(cls_id))
                action = self._map_class_to_action(class_name)
                if action is None:
                    LOGGER.debug("检测类别未映射到业务动作，已忽略: class_name=%s", class_name)
                    continue

                x1, y1, x2, y2 = [float(value) for value in bbox_xyxy]
                center_x = max(0.0, min(float(image_w), (x1 + x2) / 2.0))
                center_y = max(0.0, min(float(image_h), (y1 + y2) / 2.0))
                region_index, region_id = self._resolve_region(center_x, center_y, image_w, image_h)

                detections.append(
                    DetectionRecord(
                        frame_index=frame.index,
                        timestamp=frame.timestamp,
                        action=action,
                        class_name=class_name,
                        confidence=float(confidence),
                        bbox_xyxy=[x1, y1, x2, y2],
                        center=[center_x, center_y],
                        region_id=region_id,
                        region_index=region_index,
                        source_file=frame.file_name,
                    )
                )

        return detections

    def _aggregate(
        self,
        *,
        window_id: str,
        frames: list[FrameRecord],
        detections: list[DetectionRecord],
        metadata: dict[str, Any],
        window_start_ts: float,
        window_end_ts: float,
    ) -> dict[str, Any]:
        """按区域和时间窗口统计结果。"""
        generated_at = datetime.now().isoformat(timespec="seconds")
        region_stats: dict[str, RegionStats] = {}
        region_frame_presence: dict[tuple[int, str, str], bool] = {}

        for row in range(self.config.region_rows):
            for col in range(self.config.region_cols):
                region_id = self._region_id(row, col)
                region_stats[region_id] = RegionStats(region_id=region_id, row=row, col=col)

        serializable_detections: list[dict[str, Any]] = []
        for item in sorted(detections, key=lambda x: (x.timestamp, x.frame_index, x.region_index, x.action)):
            serializable_detections.append(asdict(item))

            stats = region_stats[item.region_id]
            frame_presence_key = (item.frame_index, item.region_id, item.action)

            if item.action == "hand_raising":
                stats.hand_raising_count += 1
                if not region_frame_presence.get(frame_presence_key):
                    stats.hand_frames += 1
                    region_frame_presence[frame_presence_key] = True
            elif item.action == "standing":
                stats.standing_count += 1
                if not region_frame_presence.get(frame_presence_key):
                    stats.standing_frames += 1
                    region_frame_presence[frame_presence_key] = True

        total_hand = 0
        total_standing = 0
        heatmap: list[list[int]] = []
        region_grid_3x3: list[list[dict[str, Any]]] = []
        active_region_count = 0
        most_active_region: dict[str, Any] | None = None
        most_active_score = -1

        for row in range(self.config.region_rows):
            heatmap_row: list[int] = []
            region_grid_row: list[dict[str, Any]] = []
            for col in range(self.config.region_cols):
                region_id = self._region_id(row, col)
                stats = region_stats[region_id]
                stats.total_events = stats.hand_raising_count + stats.standing_count
                total_hand += stats.hand_raising_count
                total_standing += stats.standing_count
                heatmap_row.append(stats.total_events)
                region_grid_row.append(
                    {
                        "region_id": region_id,
                        "row": row,
                        "col": col,
                        "hand_raising_count": stats.hand_raising_count,
                        "standing_count": stats.standing_count,
                        "total_events": stats.total_events,
                    }
                )

                if stats.total_events > 0:
                    active_region_count += 1
                if stats.total_events > most_active_score and stats.total_events > 0:
                    most_active_score = stats.total_events
                    most_active_region = {
                        "region_id": region_id,
                        "row": row,
                        "col": col,
                        "total_events": stats.total_events,
                        "hand_raising_count": stats.hand_raising_count,
                        "standing_count": stats.standing_count,
                    }
            heatmap.append(heatmap_row)
            region_grid_3x3.append(region_grid_row)

        total_events = total_hand + total_standing
        total_regions = self.config.region_rows * self.config.region_cols
        active_region_ratio = active_region_count / total_regions if total_regions else 0.0
        question_events = self._build_teacher_question_events(metadata)
        stage_distribution = self._build_stage_distribution(metadata)
        zone_summary = self._build_zone_summary(
            metadata=metadata,
            region_stats=region_stats,
            total_events=total_events,
        )
        avg_attention_ratio = self._compute_avg_attention_ratio(zone_summary, metadata)
        hand_raise_event_count = int(total_hand)
        response_success_rate = self._compute_response_success_rate(
            question_count=len(question_events),
            hand_raise_event_count=hand_raise_event_count,
        )
        attention_score = round(avg_attention_ratio * 100, 2)
        response_score = round(response_success_rate * 100, 2)
        feedback_score = self._compute_feedback_score(
            attention_score=attention_score,
            response_score=response_score,
            active_ratio=active_region_ratio,
        )
        timeline = self._build_timeline(
            metadata=metadata,
            avg_attention_ratio=avg_attention_ratio,
            active_region_ratio=active_region_ratio,
            total_events=total_events,
            total_regions=total_regions,
        )

        result = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "analysis_id": self._resolve_analysis_id(metadata, window_id, generated_at),
            "classroom_id": str(metadata.get("classroom_id") or "unknown_classroom"),
            "video_id": str(metadata.get("video_id") or window_id),
            "source": {
                "source_kind": str(metadata.get("source_kind") or "captured_video"),
                "source_path": str(metadata.get("source_path") or metadata.get("received_dir") or ""),
                "source_host": str(metadata.get("source_host") or self.config.source_host),
            },
            "time": {
                "recorded_at": self._resolve_recorded_at(metadata, window_start_ts),
                "generated_at": generated_at,
                "duration_seconds": int(metadata.get("duration_seconds") or self.config.window_seconds),
            },
            "summary": {
                "feedback_score": feedback_score,
                "attention_score": attention_score,
                "response_score": response_score,
                "teacher_question_count": len(question_events),
                "avg_attention_ratio": round(avg_attention_ratio, 4),
                "response_success_rate": round(response_success_rate, 4),
                "summary_text": self._build_summary_text(
                    question_count=len(question_events),
                    hand_raise_event_count=hand_raise_event_count,
                    avg_attention_ratio=avg_attention_ratio,
                    active_region_ratio=active_region_ratio,
                ),
            },
            "teacher": {
                "question_events": question_events,
                "stage_distribution": stage_distribution,
            },
            "students": {
                "estimated_student_count": self._resolve_estimated_student_count(metadata),
                "hand_raise_event_count": hand_raise_event_count,
                "zones": zone_summary,
            },
            "timeline": timeline,
        }

        LOGGER.info(
            "窗口统计完成: window_id=%s hand=%s standing=%s active_regions=%s feedback_score=%s",
            window_id,
            total_hand,
            total_standing,
            active_region_count,
            feedback_score,
        )
        return result

    def _write_result_json(self, output_path: Path, result_data: dict[str, Any]) -> None:
        """保存窗口结果 JSON，供本地调试和回溯使用。"""
        output_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("窗口结果已保存: %s", output_path)

    def _push_to_cloud(self, result_data: dict[str, Any], window_id: str) -> dict[str, Any]:
        """向云端推送窗口结果；失败仅记录日志，不影响本地保存流程。"""
        finished_at = datetime.now().isoformat(timespec="seconds")

        if not self.config.cloud_push_enabled:
            LOGGER.info("云端推送已禁用: window_id=%s", window_id)
            return {
                "cloud_push_status": "disabled",
                "cloud_push_time": finished_at,
                "cloud_push_attempts": 0,
                "cloud_push_http_status": None,
                "cloud_push_duration_ms": 0.0,
            }

        if not self.config.cloud_push_url:
            LOGGER.error("云端推送失败: window_id=%s reason=missing_push_url", window_id)
            return {
                "cloud_push_status": "failed",
                "cloud_push_time": finished_at,
                "cloud_push_attempts": 0,
                "cloud_push_http_status": None,
                "cloud_push_duration_ms": 0.0,
            }

        payload_text = json.dumps(result_data, ensure_ascii=False, indent=2)
        headers = dict(self.config.cloud_push_headers)
        headers["Content-Type"] = "application/json; charset=utf-8"
        total_attempts = len(CLOUD_PUSH_RETRY_DELAYS) + 1
        start_time = time.perf_counter()
        last_status_code: int | None = None
        last_error: str | None = None
        last_response_text: str | None = None

        for attempt in range(1, total_attempts + 1):
            attempt_start = time.perf_counter()
            try:
                LOGGER.info(
                    "开始推送窗口结果到云端: window_id=%s attempt=%s/%s url=%s timeout=%ss",
                    window_id,
                    attempt,
                    total_attempts,
                    self.config.cloud_push_url,
                    self.config.cloud_push_timeout,
                )
                response = requests.post(
                    self.config.cloud_push_url,
                    data=payload_text.encode("utf-8"),
                    headers=headers,
                    timeout=self.config.cloud_push_timeout,
                )
                last_status_code = response.status_code
                last_response_text = response.text
                response.raise_for_status()

                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                finished_at = datetime.now().isoformat(timespec="seconds")
                LOGGER.info(
                    "云端推送成功: window_id=%s attempt=%s/%s status_code=%s duration_ms=%.2f",
                    window_id,
                    attempt,
                    total_attempts,
                    response.status_code,
                    duration_ms,
                )
                return {
                    "cloud_push_status": "success",
                    "cloud_push_time": finished_at,
                    "cloud_push_attempts": attempt,
                    "cloud_push_http_status": response.status_code,
                    "cloud_push_duration_ms": duration_ms,
                }
            except requests.RequestException as exc:
                response = getattr(exc, "response", None)
                if response is not None:
                    last_status_code = response.status_code
                    last_response_text = response.text
                last_error = str(exc)
                attempt_duration_ms = round((time.perf_counter() - attempt_start) * 1000, 2)
                LOGGER.error(
                    "云端推送失败: window_id=%s attempt=%s/%s status_code=%s duration_ms=%.2f error=%s response=%s",
                    window_id,
                    attempt,
                    total_attempts,
                    last_status_code,
                    attempt_duration_ms,
                    last_error,
                    (last_response_text or "")[:300],
                )
            except Exception as exc:
                last_error = str(exc)
                attempt_duration_ms = round((time.perf_counter() - attempt_start) * 1000, 2)
                LOGGER.error(
                    "云端推送异常: window_id=%s attempt=%s/%s duration_ms=%.2f error=%s",
                    window_id,
                    attempt,
                    total_attempts,
                    attempt_duration_ms,
                    last_error,
                )

            if attempt < total_attempts:
                retry_delay = CLOUD_PUSH_RETRY_DELAYS[attempt - 1]
                LOGGER.info(
                    "准备重试云端推送: window_id=%s next_attempt=%s wait_seconds=%s",
                    window_id,
                    attempt + 1,
                    retry_delay,
                )
                time.sleep(retry_delay)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        finished_at = datetime.now().isoformat(timespec="seconds")
        LOGGER.error(
            "云端推送最终失败: window_id=%s attempts=%s status_code=%s duration_ms=%.2f error=%s response=%s",
            window_id,
            total_attempts,
            last_status_code,
            duration_ms,
            last_error,
            (last_response_text or "")[:300],
        )
        return {
            "cloud_push_status": "failed",
            "cloud_push_time": finished_at,
            "cloud_push_attempts": total_attempts,
            "cloud_push_http_status": last_status_code,
            "cloud_push_duration_ms": duration_ms,
        }

    def _describe_models(self) -> dict[str, Any]:
        """输出当前模型使用情况。"""
        if self.config.use_merged_model and self._merged_model is not None:
            return {
                "mode": "merged",
                "source_host": self.config.source_host,
                "config_path": str(self.config.config_path),
                "merged_model_path": str(self.config.merged_model_path),
                "class_names": list(self._merged_model.names.values()),
            }

        return {
            "mode": "separate",
            "source_host": self.config.source_host,
            "config_path": str(self.config.config_path),
            "hand_model_path": str(self.config.hand_model_path) if self.config.hand_model_path else None,
            "standing_model_path": str(self.config.standing_model_path) if self.config.standing_model_path else None,
            "hand_class_names": list(self._hand_model.names.values()) if self._hand_model else [],
            "standing_class_names": list(self._standing_model.names.values()) if self._standing_model else [],
        }

    def _resolve_analysis_id(self, metadata: dict[str, Any], window_id: str, generated_at: str) -> str:
        explicit_id = metadata.get("analysis_id")
        if explicit_id:
            return str(explicit_id)
        classroom_id = str(metadata.get("classroom_id") or "unknown")
        date_part = generated_at[:10].replace("-", "")
        safe_window_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in window_id)
        return f"{classroom_id}_{date_part}_{safe_window_id}"

    def _resolve_recorded_at(self, metadata: dict[str, Any], window_start_ts: float) -> str:
        recorded_at = metadata.get("recorded_at")
        if recorded_at:
            return self._normalize_time_value(recorded_at, fallback_ts=window_start_ts)
        return self._format_timestamp(window_start_ts)

    def _resolve_estimated_student_count(self, metadata: dict[str, Any]) -> int:
        students_cfg = metadata.get("students", {})
        if isinstance(students_cfg, dict) and students_cfg.get("estimated_student_count") is not None:
            return int(students_cfg["estimated_student_count"])
        if metadata.get("estimated_student_count") is not None:
            return int(metadata["estimated_student_count"])
        return 0

    def _build_teacher_question_events(self, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        teacher_cfg = metadata.get("teacher", {})
        explicit_events = []
        if isinstance(teacher_cfg, dict):
            explicit_events = teacher_cfg.get("question_events") or []
        if explicit_events:
            return [self._normalize_question_event(index, event) for index, event in enumerate(explicit_events, start=1)]

        transcript_segments = metadata.get("teacher_transcript_segments") or metadata.get("teacher_segments") or []
        question_events: list[dict[str, Any]] = []
        for index, segment in enumerate(transcript_segments, start=1):
            if not isinstance(segment, dict):
                continue
            text = str(segment.get("text") or "").strip()
            if not text or not self._looks_like_question(text):
                continue
            question_events.append(
                {
                    "event_id": f"q_{index:03d}",
                    "start_sec": float(segment.get("start_sec") or 0.0),
                    "end_sec": float(segment.get("end_sec") or segment.get("start_sec") or 0.0),
                    "text": text,
                    "question_type": str(segment.get("question_type") or self._infer_question_type(text)),
                }
            )
        return question_events

    def _normalize_question_event(self, index: int, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_id": str(event.get("event_id") or f"q_{index:03d}"),
            "start_sec": float(event.get("start_sec") or 0.0),
            "end_sec": float(event.get("end_sec") or event.get("start_sec") or 0.0),
            "text": str(event.get("text") or ""),
            "question_type": str(event.get("question_type") or "open_question"),
        }

    def _build_stage_distribution(self, metadata: dict[str, Any]) -> dict[str, float]:
        teacher_cfg = metadata.get("teacher", {})
        explicit = teacher_cfg.get("stage_distribution") if isinstance(teacher_cfg, dict) else None
        if isinstance(explicit, dict):
            return self._normalize_stage_distribution(explicit)

        transcript_segments = metadata.get("teacher_transcript_segments") or metadata.get("teacher_segments") or []
        stage_durations = {
            "exposition_ratio": 0.0,
            "question_ratio": 0.0,
            "discussion_ratio": 0.0,
            "summary_ratio": 0.0,
            "management_ratio": 0.0,
        }
        total_duration = 0.0
        for segment in transcript_segments:
            if not isinstance(segment, dict):
                continue
            text = str(segment.get("text") or "")
            start_sec = float(segment.get("start_sec") or 0.0)
            end_sec = float(segment.get("end_sec") or start_sec)
            duration = max(end_sec - start_sec, 0.0)
            if duration <= 0:
                continue
            total_duration += duration
            stage_key = self._classify_stage_from_text(text)
            stage_durations[stage_key] += duration

        if total_duration <= 0:
            return {key: 0.0 for key in stage_durations}
        return {key: round(value / total_duration, 4) for key, value in stage_durations.items()}

    def _normalize_stage_distribution(self, distribution: dict[str, Any]) -> dict[str, float]:
        keys = (
            "exposition_ratio",
            "question_ratio",
            "discussion_ratio",
            "summary_ratio",
            "management_ratio",
        )
        return {key: round(float(distribution.get(key, 0.0)), 4) for key in keys}

    def _build_zone_summary(
        self,
        *,
        metadata: dict[str, Any],
        region_stats: dict[str, RegionStats],
        total_events: int,
    ) -> dict[str, dict[str, float]]:
        explicit_zones = {}
        students_cfg = metadata.get("students", {})
        if isinstance(students_cfg, dict):
            explicit_zones = students_cfg.get("zones") or {}

        zone_rows = {"front": 0, "middle": 1, "back": 2}
        zones: dict[str, dict[str, float]] = {}
        for zone_name, row_index in zone_rows.items():
            matching_stats = [
                stats
                for stats in region_stats.values()
                if stats.row == row_index
            ]
            zone_total_events = sum(stats.total_events for stats in matching_stats)
            explicit_zone_cfg = explicit_zones.get(zone_name, {}) if isinstance(explicit_zones, dict) else {}
            avg_attention_ratio = explicit_zone_cfg.get("avg_attention_ratio")
            if avg_attention_ratio is None:
                avg_attention_ratio = 0.0
            active_ratio = explicit_zone_cfg.get("active_ratio")
            if active_ratio is None:
                active_ratio = (zone_total_events / total_events) if total_events else 0.0
            zones[zone_name] = {
                "avg_attention_ratio": round(float(avg_attention_ratio), 4),
                "active_ratio": round(float(active_ratio), 4),
            }
        return zones

    def _compute_avg_attention_ratio(self, zone_summary: dict[str, dict[str, float]], metadata: dict[str, Any]) -> float:
        students_cfg = metadata.get("students", {})
        if isinstance(students_cfg, dict) and students_cfg.get("avg_attention_ratio") is not None:
            return float(students_cfg["avg_attention_ratio"])
        zone_values = [zone["avg_attention_ratio"] for zone in zone_summary.values()]
        return (sum(zone_values) / len(zone_values)) if zone_values else 0.0

    def _compute_response_success_rate(self, *, question_count: int, hand_raise_event_count: int) -> float:
        if question_count <= 0:
            return 0.0
        return min(hand_raise_event_count / question_count, 1.0)

    def _compute_feedback_score(self, *, attention_score: float, response_score: float, active_ratio: float) -> float:
        return round(min(max((0.45 * attention_score) + (0.4 * response_score) + (0.15 * active_ratio * 100), 0.0), 100.0), 2)

    def _build_timeline(
        self,
        *,
        metadata: dict[str, Any],
        avg_attention_ratio: float,
        active_region_ratio: float,
        total_events: int,
        total_regions: int,
    ) -> dict[str, Any]:
        timeline_cfg = metadata.get("timeline", {})
        if not isinstance(timeline_cfg, dict):
            timeline_cfg = {}

        window_size_seconds = int(timeline_cfg.get("window_size_seconds") or self.config.window_seconds)
        attention_curve = self._normalize_curve(timeline_cfg.get("attention_curve"), fallback_value=avg_attention_ratio)
        heat_curve = self._normalize_curve(timeline_cfg.get("heat_curve"), fallback_value=0.0)
        activity_fallback = (total_events / max(total_regions, 1)) if total_regions else 0.0
        activity_curve = self._normalize_curve(
            timeline_cfg.get("activity_curve"),
            fallback_value=max(activity_fallback, active_region_ratio),
        )

        target_length = max(len(attention_curve), len(heat_curve), len(activity_curve))
        attention_curve = self._pad_curve(attention_curve, target_length)
        heat_curve = self._pad_curve(heat_curve, target_length)
        activity_curve = self._pad_curve(activity_curve, target_length)

        return {
            "window_size_seconds": window_size_seconds,
            "attention_curve": attention_curve,
            "heat_curve": heat_curve,
            "activity_curve": activity_curve,
        }

    def _normalize_curve(self, value: Any, *, fallback_value: float) -> list[float]:
        if isinstance(value, list) and value:
            return [round(float(item), 4) for item in value]
        return [round(float(fallback_value), 4)]

    def _pad_curve(self, curve: list[float], target_length: int) -> list[float]:
        if not curve:
            curve = [0.0]
        if len(curve) >= target_length:
            return curve
        last_value = curve[-1]
        return curve + [last_value] * (target_length - len(curve))

    def _build_summary_text(
        self,
        *,
        question_count: int,
        hand_raise_event_count: int,
        avg_attention_ratio: float,
        active_region_ratio: float,
    ) -> str:
        if question_count == 0 and hand_raise_event_count == 0:
            return "当前窗口未检测到明显提问或举手响应。"
        if question_count > 0 and hand_raise_event_count == 0:
            return "检测到教师提问，但当前窗口未观察到明显举手响应。"
        if avg_attention_ratio < 0.4:
            return "当前窗口整体注意力偏低，互动信号较弱。"
        if active_region_ratio > 0.5:
            return "当前窗口多个区域出现互动，课堂响应较活跃。"
        return "当前窗口检测到课堂互动信号，适合继续结合时间线查看。"

    def _normalize_time_value(self, value: Any, *, fallback_ts: float) -> str:
        if value is None or value == "":
            return self._format_timestamp(fallback_ts)
        if isinstance(value, (int, float)):
            return self._format_timestamp(float(value))
        text = str(value).strip()
        if not text:
            return self._format_timestamp(fallback_ts)
        try:
            return self._format_timestamp(float(text))
        except ValueError:
            return text

    def _looks_like_question(self, text: str) -> bool:
        normalized = text.strip()
        question_markers = (
            "?",
            "？",
            "谁来回答",
            "为什么",
            "有没有同学知道",
            "你来说一下",
            "大家想一想",
            "大家说",
            "知道吗",
            "请举手",
            "举手",
            "是否正确",
            "对还是错",
            "是多少",
            "等于几",
            "怎么",
            "怎么来",
            "吗",
            "么",
        )
        return any(marker in normalized for marker in question_markers)

    def _infer_question_type(self, text: str) -> str:
        normalized = text.strip()
        if any(keyword in normalized for keyword in ("请举手", "同意的请举手", "认为错的举手", "做完答案的请举手", "举手")):
            return "hand_raise_prompt"
        if any(keyword in normalized for keyword in ("大家说", "知道吗", "你认为对还是错", "大家想一想")):
            return "collective_response"
        if any(keyword in normalized for keyword in ("是否正确", "对还是错")):
            return "correctness_check"
        if any(keyword in normalized for keyword in ("是多少", "等于几")):
            return "closed_question"
        return "open_question"

    def _classify_stage_from_text(self, text: str) -> str:
        normalized = text.strip()
        if not normalized:
            return "exposition_ratio"
        if self._looks_like_question(normalized):
            return "question_ratio"
        if any(keyword in normalized for keyword in ("讨论", "交流", "小组", "互相")):
            return "discussion_ratio"
        if any(keyword in normalized for keyword in ("总结", "回顾", "归纳")):
            return "summary_ratio"
        if any(keyword in normalized for keyword in ("安静", "看这里", "坐好", "不要", "纪律")):
            return "management_ratio"
        return "exposition_ratio"

    def _map_class_to_action(self, class_name: str) -> str | None:
        """将模型类别名映射到业务动作名。"""
        normalized = class_name.strip().lower().replace(" ", "-").replace("_", "-")
        hand_set = {name.lower().replace("_", "-") for name in self.config.hand_class_names}
        standing_set = {name.lower().replace("_", "-") for name in self.config.standing_class_names}

        if normalized in hand_set:
            return "hand_raising"
        if normalized in standing_set:
            return "standing"
        return None

    def _resolve_region(self, center_x: float, center_y: float, image_w: int, image_h: int) -> tuple[int, str]:
        """依据检测框中心点落入 3x3 网格区域。"""
        col = min(self.config.region_cols - 1, int(center_x / max(1, image_w) * self.config.region_cols))
        row = min(self.config.region_rows - 1, int(center_y / max(1, image_h) * self.config.region_rows))
        region_index = row * self.config.region_cols + col
        return region_index, self._region_id(row, col)

    def _calculate_overall_feedback_score(
        self,
        *,
        total_events: int,
        frame_count: int,
        interaction_rate: float,
        active_region_ratio: float,
    ) -> float:
        """计算总体课堂反馈分数。

        计算公式：
        1. normalized_interaction_rate = min(interaction_rate, 1.0)
        2. normalized_event_density = min(total_events / max(frame_count, 1), 1.0)
        3. overall_feedback_score =
           (0.5 * normalized_interaction_rate
            + 0.3 * active_region_ratio
            + 0.2 * normalized_event_density) * 100

        说明：
        - 互动率权重 50%
        - 活跃区域比例权重 30%
        - 单窗口事件密度权重 20%
        - 最终结果限制在 0-100 分之间
        """
        normalized_interaction_rate = min(max(interaction_rate, 0.0), 1.0)
        normalized_event_density = min(max(total_events / max(frame_count, 1), 0.0), 1.0)
        raw_score = (
            0.5 * normalized_interaction_rate
            + 0.3 * max(active_region_ratio, 0.0)
            + 0.2 * normalized_event_density
        ) * 100.0
        return round(min(max(raw_score, 0.0), 100.0), 2)

    @staticmethod
    def _region_id(row: int, col: int) -> str:
        return f"R{row + 1}C{col + 1}"

    @staticmethod
    def _to_unix_timestamp(value: str | float | int | None) -> float | None:
        """兼容多种时间戳输入格式。"""
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if not text:
            return None

        try:
            return float(text)
        except ValueError:
            pass

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except ValueError:
            LOGGER.warning("不支持的时间戳格式: %s", value)
            return None

    @staticmethod
    def _format_timestamp(timestamp: float) -> str:
        """将 Unix 时间戳格式化为 ISO 8601 文本。"""
        return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def build_default_processor(config_path: str | Path | None = None) -> YoloInteractionProcessor:
    """构建默认处理器。"""
    configure_logging(config_path)
    config = load_processor_config(config_path)
    return YoloInteractionProcessor(config=config)


def validate_result_payload(result_data: dict[str, Any]) -> dict[str, Any]:
    """校验结果 JSON 是否满足本地到云端主链路的最小字段契约。"""
    summary = result_data.get("summary", {})
    source = result_data.get("source", {})
    time_block = result_data.get("time", {})
    teacher = result_data.get("teacher", {})
    students = result_data.get("students", {})
    timeline = result_data.get("timeline", {})
    missing_root_fields = [field for field in REQUIRED_RESULT_ROOT_FIELDS if field not in result_data]
    missing_summary_fields = [field for field in REQUIRED_SUMMARY_FIELDS if field not in summary]
    missing_source_fields = [
        field for field in ("source_kind", "source_path", "source_host")
        if field not in source
    ]
    missing_time_fields = [
        field for field in ("recorded_at", "generated_at", "duration_seconds")
        if field not in time_block
    ]
    missing_teacher_fields = [
        field for field in ("question_events", "stage_distribution")
        if field not in teacher
    ]
    missing_students_fields = [
        field for field in ("estimated_student_count", "hand_raise_event_count", "zones")
        if field not in students
    ]
    missing_timeline_fields = [
        field for field in ("window_size_seconds", "attention_curve", "heat_curve", "activity_curve")
        if field not in timeline
    ]
    curve_lengths = [
        len(timeline.get("attention_curve", [])),
        len(timeline.get("heat_curve", [])),
        len(timeline.get("activity_curve", [])),
    ]
    curves_same_length = len(set(curve_lengths)) == 1 if all(length > 0 for length in curve_lengths) else False
    return {
        "is_valid": (
            not missing_root_fields
            and not missing_summary_fields
            and not missing_source_fields
            and not missing_time_fields
            and not missing_teacher_fields
            and not missing_students_fields
            and not missing_timeline_fields
            and curves_same_length
        ),
        "missing_root_fields": missing_root_fields,
        "missing_summary_fields": missing_summary_fields,
        "missing_source_fields": missing_source_fields,
        "missing_time_fields": missing_time_fields,
        "missing_teacher_fields": missing_teacher_fields,
        "missing_students_fields": missing_students_fields,
        "missing_timeline_fields": missing_timeline_fields,
        "curves_same_length": curves_same_length,
    }
