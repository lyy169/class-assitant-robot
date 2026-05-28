# Pi Session Delivery V1

## Scope

This spec defines the formal session delivery boundary from the Raspberry Pi edge runtime to the local analysis side.

This session delivery mainline:
- only covers capture and delivery
- does not cover classroom analysis, scoring, or event extraction
- does not replace the legacy realtime dialogue or legacy voice-triggered recording mainline

## Formal Session Directory

The formal delivered session directory is:

```text
captures/{classroom_id}/{date}/{session_id}/
  video.mp4
  audio.wav
  metadata.json
  teacher_transcript.json
```

`date` uses `YYYY-MM-DD`.

`session_id` is the runtime-generated unique capture directory name.

## Minimum Required Files

The local side must be able to rely on these four files:

- `video.mp4`
- `audio.wav`
- `metadata.json`
- `teacher_transcript.json`

These four filenames are fixed within a session directory and are not negotiable in V1.

## `metadata.json` Minimum Required Fields

The minimum required metadata fields are:

```json
{
  "capture_id": "cap_20260420_001",
  "classroom_id": "classroom-a",
  "source_host": "raspberrypi-01",
  "started_at": "2026-04-20T09:30:00+08:00",
  "ended_at": "2026-04-20T09:30:12+08:00",
  "duration_seconds": 12.0,
  "transcript_source": "azure_stt",
  "delivery_path": "captures_local_delivery/classroom-a/2026-04-20/session-001",
  "status": "completed"
}
```

The current formal V1 metadata contract should also carry these fields when available:

- `device_id`
- `local_video_path`
- `local_audio_path`
- `transcript_path`
- `transcript_status`
- `delivery_mode`
- `error`

## `teacher_transcript.json` Fixed Structure

`teacher_transcript.json` must be a JSON array.

Each item must have exactly these semantic fields:

```json
[
  {
    "start_sec": 12.4,
    "end_sec": 15.8,
    "text": "谁来回答一下这个问题",
    "speaker": "teacher"
  }
]
```

Rules:
- `start_sec` is a number
- `end_sec` is a number
- `text` is a string
- `speaker` is fixed to `teacher` in V1
- no transcript-source field is stored in this file
- transcript source is tracked in `metadata.json`

## Delivery Mode

The current formal delivery mode is:

- `shared_dir`

Interpretation:
- the Pi runtime writes the session directory locally first
- after capture finalization, it copies the completed session directory into the configured local delivery root
- the local analysis side consumes the copied session directory as a stable input

V1 does not define:
- message queue delivery
- task orchestration
- cloud-side analysis triggers

## Failure Downgrade Policy

### Transcript unavailable

If transcript generation is unavailable:

- `teacher_transcript.json` must still be generated
- its content must be `[]`
- `metadata.json.transcript_status` must be `unavailable`
- `metadata.json.transcript_source` must be `unavailable`
- capture completion must not be downgraded to `failed` only because transcript is unavailable

### Capture failed

If capture itself fails:

- `metadata.json.status` must be `failed`
- `metadata.json.error` must contain the failure reason
- `teacher_transcript.json` may be `[]`
- `delivery_path` may be empty if delivery was never completed

## Boundary With Legacy Mainlines

This session delivery mainline is separate from:

- legacy realtime dialogue mainline
- legacy voice-triggered recording mainline
- legacy upload watcher mainline

V1 requirements:
- do not route `server.py` through this session mainline
- do not replace the legacy recording path in this round
- do not bind classroom analysis to the Pi runtime

## Formal Responsibility Boundary

The Pi session delivery mainline is formally responsible for:

- capture session directory creation
- `video.mp4` generation
- `audio.wav` generation
- `metadata.json` generation
- `teacher_transcript.json` generation
- copying the completed session into the shared delivery directory

The Pi session delivery mainline is not responsible for:

- classroom scoring
- teacher performance analysis
- student behavior analysis
- event extraction beyond raw transcript segments
- cloud-side result processing

## Current Repository Constraint

The current `video_project_src` workspace is the cloud-side source repository.

This repository currently documents the Pi session delivery contract, but it does not contain the active Pi runtime files referenced in prior edge work such as:

- `capture_session.py`
- `pi_capture_runtime.py`
- `pi_transcript_delivery.py`

Therefore, in this workspace, V1 is formalized as:

- a normative spec
- a stable sample session directory
- an execution record

Code-level runtime enforcement must be completed in the actual Pi runtime repository or in a later sync that imports those edge runtime files into source control.
