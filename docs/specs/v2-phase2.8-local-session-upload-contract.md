# V2 Phase 2.8 Contract: Local Analyzer Session Upload

## 1. Purpose

Define how the local analyzer side should assemble and upload Phase 2.8 classroom session JSON.

## 2. Responsibility

The local analyzer is responsible for:

- reading Raspberry Pi capture metadata
- running YOLO and classroom behavior analysis
- generating the existing V1.1 classroom analysis payload
- merging `source`, `capture`, `video`, and `upload` metadata
- preserving teacher question events and question summary when available
- uploading JSON to cloud through `POST /api/interaction-results`
- auditing local video format capability

## 3. Required Existing Payload Fields

Do not remove existing fields:

- `schema_version`
- `analysis_id`
- `classroom_id`
- `video_id`
- `source`
- `time`
- `summary`
- `teacher`
- `students`
- `timeline`

## 4. Required Metadata Blocks

Final JSON should include:

```json
{
  "source": {
    "source_kind": "local_analyzer",
    "source_host": "local-pc-lab-01",
    "source_path": "/data/classroom_101/session_001/result.json"
  },
  "capture": {
    "device_id": "pi-classroom-101",
    "device_name": "Raspberry Pi - Classroom 101",
    "classroom_id": "classroom_101",
    "captured_at": "2026-04-29T09:00:00+08:00",
    "video_path": "/data/classroom_101/session_001/video.mp4",
    "keyframe_dir": "/data/classroom_101/session_001/keyframes"
  },
  "video": {
    "video_id": "video_20260429_101_001",
    "raw_video_path": "/data/classroom_101/session_001/video.mp4",
    "video_url": "",
    "duration_seconds": 600,
    "format": "mp4",
    "codec": "h264",
    "browser_compatible": true,
    "transcode_capability": "present"
  },
  "upload": {
    "uploaded_at": "2026-04-29T09:30:00+08:00",
    "target": "cloud_backend",
    "api": "/api/interaction-results",
    "client_version": "local-analyzer-v1"
  }
}
```

## 5. Teacher Question Preservation

If available, preserve:

```json
{
  "teacher": {
    "question_events": [],
    "question_summary": {
      "total_count": 0,
      "open_question_count": 0,
      "closed_question_count": 0,
      "response_count": 0,
      "response_rate": 0
    }
  }
}
```

Phase 2.8 does not require deep question guidance analysis.

## 6. Video Format Capability Audit

The local analyzer should check whether video format standardization already exists.

Look for:

- `ffmpeg`
- `moviepy`
- OpenCV `VideoWriter`
- `subprocess` calling ffmpeg
- scripts or functions named `standardize`, `convert`, `transcode`, `h264`, `aac`

Output markers:

```text
LOCAL_VIDEO_TRANSCODE_CAPABILITY=present/absent/unknown
LOCAL_VIDEO_OUTPUT_BROWSER_COMPATIBLE=true/false/unknown
```

This is an audit only. Phase 2.8 does not require new transcoding implementation.

## 7. Upload Rule

Upload endpoint:

```http
POST /api/interaction-results
```

Recommended local behavior:

- validate JSON before upload
- preserve local copy of uploaded JSON
- log cloud response
- record request id or saved path from cloud response

## 8. Validation Markers

Local analyzer validation should output:

```text
LOCAL_SESSION_JSON_VALID=true
LOCAL_SOURCE_PRESENT=true
LOCAL_CAPTURE_PRESENT=true
LOCAL_VIDEO_PRESENT=true
LOCAL_UPLOAD_PRESENT=true
LOCAL_TEACHER_QUESTION_EVENTS_PRESERVED=true/false
LOCAL_VIDEO_TRANSCODE_CAPABILITY=present/absent/unknown
LOCAL_VIDEO_OUTPUT_BROWSER_COMPATIBLE=true/false/unknown
LOCAL_CLOUD_UPLOAD_SUCCESS=true
```

## 9. Non-Goals

Do not implement in Phase 2.8:

- YOLO algorithm rewrite
- automatic cloud video upload
- new transcoding service
- heartbeat protocol
- permission system

