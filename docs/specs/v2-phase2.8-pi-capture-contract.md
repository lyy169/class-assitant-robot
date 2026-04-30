# V2 Phase 2.8 Contract: Raspberry Pi Capture Side

## 1. Purpose

Define the minimum capture metadata that the Raspberry Pi side must provide for Phase 2.8 ingestion status.

This contract does not require the Raspberry Pi side to upload directly to cloud.

The Raspberry Pi project may be edited through SSHFS. SSHFS is only treated as a file editing and document synchronization channel. Runtime operations that depend on the Raspberry Pi environment, camera device, local media paths, or installed codecs must be packaged as scripts and run by the operator on the Raspberry Pi itself.

## 2. Responsibility

Raspberry Pi side is responsible for:

- classroom video or keyframe capture
- stable capture device identity
- classroom identity
- capture timestamp
- paths to captured media or keyframes

Raspberry Pi side is not responsible for:

- YOLO analysis
- cloud upload
- final classroom analysis JSON
- cloud video formatting
- heartbeat service

## 3. Required Output

Recommended metadata file:

```text
capture_metadata.json
```

Recommended content:

```json
{
  "capture": {
    "device_id": "pi-classroom-101",
    "device_name": "Raspberry Pi - Classroom 101",
    "classroom_id": "classroom_101",
    "captured_at": "2026-04-29T09:00:00+08:00",
    "video_path": "/data/classroom_101/session_001/video.mp4",
    "keyframe_dir": "/data/classroom_101/session_001/keyframes"
  }
}
```

## 4. Required Fields

Must provide:

- `capture.device_id`
- `capture.classroom_id`
- `capture.captured_at`

Should provide:

- `capture.device_name`
- `capture.video_path`
- `capture.keyframe_dir`

## 5. Field Rules

`device_id`:

- stable
- machine-readable
- example: `pi-classroom-101`

`device_name`:

- display-friendly
- example: `Raspberry Pi - Classroom 101`

`classroom_id`:

- should match cloud classroom id

`captured_at`:

- ISO 8601 timestamp
- timezone preferred

`video_path`:

- local path or shared path for the captured classroom video

`keyframe_dir`:

- local path or shared path for keyframes

## 6. Delivery To Local Analyzer

Allowed delivery methods:

- metadata JSON file in the session folder
- command-line argument
- sidecar file copied with video/keyframes

Recommended session folder:

```text
session_001/
  video.mp4
  keyframes/
  capture_metadata.json
```

## 7. Validation Markers

Raspberry Pi side validation should be provided as a script, recommended path:

```text
scripts/validate_capture_metadata.sh
```

The script must be safe to run on the Raspberry Pi device and should not require Codex to access camera hardware through SSHFS.

Raspberry Pi side validation should output:

```text
PI_CAPTURE_METADATA_VALID=true
PI_CAPTURE_DEVICE_ID_PRESENT=true
PI_CAPTURE_CLASSROOM_ID_PRESENT=true
PI_CAPTURE_TIME_PRESENT=true
PI_CAPTURE_VIDEO_PATH_PRESENT=true/false
PI_CAPTURE_KEYFRAME_DIR_PRESENT=true/false
```

## 8. Non-Goals

Do not implement in Phase 2.8:

- direct cloud upload
- heartbeat API
- device registration
- video transcoding
- YOLO analysis changes
