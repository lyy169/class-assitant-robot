# Pi Session Delivery Iteration 01

## 1. Goal

This iteration formalizes the Raspberry Pi session delivery mainline as a stable downstream input boundary for the local analysis side.

The target for this round was:
- define the formal session delivery spec
- lock the stable session directory contract
- provide concrete metadata and transcript examples
- record validation honestly without claiming Pi runtime execution that did not happen in this workspace

## 2. Modified Files

Files added in this iteration:

- `docs/specs/pi-session-delivery-v1.md`
- `samples/pi-session-delivery-v1/example-classroom/2026-04-20/session-demo/metadata.json`
- `samples/pi-session-delivery-v1/example-classroom/2026-04-20/session-demo/teacher_transcript.json`

Files expected to exist in the sample session directory after placeholder creation:

- `samples/pi-session-delivery-v1/example-classroom/2026-04-20/session-demo/video.mp4`
- `samples/pi-session-delivery-v1/example-classroom/2026-04-20/session-demo/audio.wav`

## 3. Updated Spec Path

Formal spec path:

- `docs/specs/pi-session-delivery-v1.md`

## 4. Formal Session Directory Structure

Current formal session delivery structure:

```text
captures/{classroom_id}/{date}/{session_id}/
  video.mp4
  audio.wav
  metadata.json
  teacher_transcript.json
```

In this repository, the contract is represented by the sample directory:

```text
samples/pi-session-delivery-v1/example-classroom/2026-04-20/session-demo/
  video.mp4
  audio.wav
  metadata.json
  teacher_transcript.json
```

## 5. `metadata.json` Example

Current example:

```json
{
  "capture_id": "cap_20260420_001",
  "classroom_id": "example-classroom",
  "device_id": "pi-demo-01",
  "source_host": "raspberrypi-demo",
  "started_at": "2026-04-20T09:30:00+08:00",
  "ended_at": "2026-04-20T09:30:12+08:00",
  "duration_seconds": 12.0,
  "local_video_path": "captures/example-classroom/2026-04-20/session-demo/video.mp4",
  "local_audio_path": "captures/example-classroom/2026-04-20/session-demo/audio.wav",
  "transcript_path": "captures/example-classroom/2026-04-20/session-demo/teacher_transcript.json",
  "transcript_status": "completed",
  "transcript_source": "chat_cache",
  "delivery_mode": "shared_dir",
  "delivery_path": "captures_local_delivery/example-classroom/2026-04-20/session-demo",
  "status": "completed",
  "error": ""
}
```

## 6. `teacher_transcript.json` Example

Current example:

```json
[
  {
    "start_sec": 0.0,
    "end_sec": 3.2,
    "text": "同学们把书翻到第三页",
    "speaker": "teacher"
  },
  {
    "start_sec": 3.2,
    "end_sec": 7.8,
    "text": "我们先看第一道题",
    "speaker": "teacher"
  },
  {
    "start_sec": 7.8,
    "end_sec": 12.0,
    "text": "谁来回答一下这个问题",
    "speaker": "teacher"
  }
]
```

## 7. Validation Method And Result

### Structure validation

Completed:
- verified that the current repository is the cloud-side source repository
- verified that this repository does not currently contain the active Pi runtime files such as `capture_session.py` and `pi_capture_runtime.py`
- formalized the session directory contract in spec form

Result:
- structure validation passed for the contract definition
- code-level Pi runtime validation was not possible in this workspace

### Directory validation

Completed:
- created a stable sample session directory under `samples/pi-session-delivery-v1/...`
- ensured the intended four-path contract is explicit

Result:
- sample session directory contract passed

### Object validation

Completed:
- created `metadata.json` example
- created `teacher_transcript.json` example

Result:
- JSON examples are valid contract examples for local-side consumption

### Command validation

Completed:
- repository inspection commands confirmed the current branch and managed scope
- repository inspection confirmed the absence of Pi runtime implementation files in this workspace

Result:
- command-level validation passed for repository state discovery
- no runtime command such as `python capture_session.py start` could be executed here because the file does not exist in this workspace

### Sample validation

Completed:
- added a formal sample session directory for downstream contract review

Result:
- sample validation passed

### True hardware validation

Not completed in this workspace.

Reason:
- this repository is not the Pi runtime repository
- no actual capture runtime is present here

## 8. Current Unresolved Problems

1. The active Pi runtime files are not present in `video_project_src`, so code-level session delivery enforcement was not executed in this repository.
2. The sample `video.mp4` and `audio.wav` in this repository are placeholders for contract completeness, not real media captures.
3. Real `shared_dir` copy validation still needs to happen in the actual Pi runtime workspace or on the device.

## 9. Next Iteration Suggestions

1. Import the actual Pi runtime session delivery files into source control or switch to the correct Pi runtime repository before attempting code-level hardening.
2. Run one real capture session on the Raspberry Pi and persist the resulting four-file session directory as a validation artifact.
3. Add a local-side ingestion validator that checks `metadata.json` and `teacher_transcript.json` against the formal V1 contract.
