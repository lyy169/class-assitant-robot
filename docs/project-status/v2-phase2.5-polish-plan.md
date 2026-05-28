# V2 Phase 2.5 Polish Plan

## Status

Planning ready for CLI Codex execution.

## Trigger

After Phase 2.5 implementation, screenshots showed the dashboard is functionally working but still has presentation issues:

- old raw/text detail sections remain visible
- raw snapshot can show `No result selected` while charts show a selected result
- first screen is not yet strong enough for competition demo
- video playback needs a stable demo route

The user has placed a demo video named `video.mp4` under the running `video_project` upload folder.

The SSHFS workspace confirms the plural folder exists:

```text
X:\video_project\uploads
```

So the expected Linux runtime path is:

```text
/root/video_project/uploads/video.mp4
```

Follow-up note:

- The manually copied video may not open directly in the browser.
- Treat this as media compatibility, not as a dashboard failure.
- Polish should include an explicit offline transcode step to produce:

```text
/root/video_project/uploads/demo_classroom_101.mp4
```

using H.264/AAC MP4 with `faststart`.

## Confirmed Direction

Polish phase should:

- keep scope limited to Phase 2.5 presentation quality
- expose `/uploads/video.mp4` through FastAPI static serving
- expose `/uploads/demo_classroom_101.mp4` when transcoded demo video exists
- bind demo video to detail fallback when payload has no explicit video URL
- make video player visible for the demo result
- fold or hide debug-looking old text sections
- improve chart readability
- keep all existing APIs stable

## Related Documents

- `docs/specs/v2-phase2.5-polish-spec.md`
- `docs/tasks/v2-phase2.5-polish-tasks.md`
- `docs/specs/v2-phase2.5-workbench-spec.md`
- `docs/tasks/v2-phase2.5-result-workbench-tasks.md`
- `docs/runbooks/v2-phase2.5-validation-runbook.md`
