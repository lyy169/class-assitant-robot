# Cloud Capability Integration Next Steps

## Current Priority

The highest-value next step is not to merge old code.

The highest-value next step is to strengthen the new cloud mainline so it becomes the clear teacher-facing center.

That means:

- improve `cloud_backend` query/read capability
- improve the teacher-facing dashboard
- define retained MP4 interface requirements clearly

## Recommended Next 1-2 Rounds

### Round A

Focus on new-mainline result viewing:

- add recent-result history query
- add classroom filtering
- make the dashboard show latest + recent windows
- keep sample-data support for safe prototype validation

### Round B

Focus on retained MP4 capability planning without code merge:

- define the formal MP4 interface contract to preserve
- document how dashboard pages should link to classroom video
- decide whether video list / stream should be wrapped or migrated first

## Old Capabilities To Leave Undisturbed For Now

These should stay documented but not actively refactored yet:

- old Flask login flow
- old Flask video page shell
- old template-based pages
- old session-based teacher/user logic
- old live frame upload / MJPEG flow
- old mock dashboard stats API

## Capabilities Most Likely To Enter The New Dashboard Later

Most likely future additions to the new dashboard:

- latest result + recent results
- classroom participation trend
- interaction-count trend
- grid / area summary trend
- linked MP4 playback or MP4 entry cards

## Practical Near-Term Rule

For the next phase:

- do not merge old code first
- do not rebuild old pages first
- do not expand auth/admin flows first

Do first:

1. make `cloud_backend` the trusted results-viewing center
2. make retained MP4 capabilities easy to connect at the display/interface level
3. delay code consolidation until those two layers are stable
