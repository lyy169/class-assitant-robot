from __future__ import annotations

import os

import const_config


class _Settings:
    """Compatibility settings for the Pi capture modules."""

    use_deepseek = const_config.use_deepseek
    use_openai = const_config.use_openai
    use_spark = const_config.use_spark

    siliconflow_api_key = const_config.sfapikey
    openai_api_key = const_config.openapikey
    spark_api_appid = const_config.sparkapi_appid
    spark_api_secret = const_config.sparkapi_secret
    spark_api_key = const_config.sparkapi_key
    azure_key = const_config.azure_key

    proxy = getattr(const_config, "proxy", {})
    chat_or_standard = const_config.chat_or_standard
    use_online_recognize = const_config.use_online_recognize
    snowboy_enable = const_config.snowboy_enable
    snowboy_path = const_config.snowboypath
    gpio_wake_enable = const_config.gpio_wake_enable

    keyframe_camera_id = 0
    keyframe_receiver_url = "http://127.0.0.1:8000/api/keyframes"
    keyframe_log_file = "Log/keyframe_capture.log"

    pi_upload_url = "http://8.148.205.228/api/videos/upload"
    pi_upload_watch_dir = "videos_to_upload"
    pi_upload_log_file = "upload_watcher.log"
    pi_ffmpeg_bin = os.environ.get("PI_FFMPEG_BIN", "ffmpeg")
    pi_ffprobe_bin = os.environ.get("PI_FFPROBE_BIN", "ffprobe")

    pi_capture_root = os.environ.get("PI_CAPTURE_ROOT", "captures")
    pi_capture_delivery_mode = os.environ.get("PI_CAPTURE_DELIVERY_MODE", "shared_dir")
    pi_local_delivery_root = os.environ.get(
        "PI_LOCAL_DELIVERY_ROOT",
        "captures_local_delivery",
    )
    pi_capture_pid_file = os.environ.get("PI_CAPTURE_PID_FILE", "captures/.capture_session.pid")
    pi_capture_state_file = os.environ.get(
        "PI_CAPTURE_STATE_FILE", "captures/.capture_session_state.json"
    )
    pi_capture_camera_id = int(os.environ.get("PI_CAPTURE_CAMERA_ID", "0"))
    pi_capture_audio_device_index = int(os.environ.get("PI_CAPTURE_AUDIO_DEVICE_INDEX", "-1"))
    pi_capture_video_fps = int(os.environ.get("PI_CAPTURE_VIDEO_FPS", "25"))
    pi_capture_frame_width = int(os.environ.get("PI_CAPTURE_FRAME_WIDTH", "1280"))
    pi_capture_frame_height = int(os.environ.get("PI_CAPTURE_FRAME_HEIGHT", "720"))
    pi_device_id = os.environ.get("PI_DEVICE_ID", "")
    pi_device_name = os.environ.get("PI_DEVICE_NAME", "")
    pi_default_classroom_id = os.environ.get("PI_DEFAULT_CLASSROOM_ID", "classroom-default")


settings = _Settings()
