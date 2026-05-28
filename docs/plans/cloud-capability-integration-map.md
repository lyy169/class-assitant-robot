# Cloud Capability Integration Map

## Scope

This document maps the current cloud-side capabilities across:

- the new formal mainline in `cloud_backend/`
- the older capabilities still present in `video_project/`

The purpose is not to merge code immediately. The purpose is to decide:

- what should remain on the formal mainline
- what should be retained but not yet migrated
- what should stay as legacy
- what order the cloud-side integration should follow

## A. Current Mainline Capability Summary

### Table 1: New Mainline Capabilities (`cloud_backend`)

| Capability | Current Status | Value To Teacher / System | Needs Further Enhancement |
| --- | --- | --- | --- |
| Health check | Implemented via `GET /health` | Confirms service is alive for operations and demos | Low |
| Classroom interaction result ingestion | Implemented via `POST /api/interaction-results` | Core cloud write path for local YOLO results | Yes |
| Payload validation | Implemented through Pydantic and config-based required fields | Prevents malformed result data entering storage | Yes |
| Raw JSON persistence | Implemented via file landing under `cloud_backend/data/raw/` | Keeps source-of-truth result payloads | Yes |
| Latest result query | Implemented via `GET /api/latest-interaction-result` | Gives a teacher-readable latest-result API | Yes |
| Minimal dashboard display | Implemented via `GET /dashboard` | Provides a single simple viewing entry for demos and teacher reading | Yes |
| Sample data fallback | Implemented through `cloud_backend/sample_data/` | Supports source-side prototype validation without touching live runtime data | Medium |
| Data model planning | Documented in `docs/plans/cloud-data-model-plan.md` | Prepares future database-backed reads and dashboard growth | Yes |

### Mainline Coverage Conclusion

`cloud_backend/` already covers the formal classroom interaction cloud loop:

1. receive result
2. validate result
3. persist result
4. read back latest result
5. display latest result

What it still does not cover:

- historical result queries
- classroom filtering
- teacher auth / user model
- MP4 upload management
- integrated “single teacher portal” spanning video + interaction data
- database-backed query performance

## B. Older Cloud-Side Capability Inventory

### Table 2: Older Capabilities Worth Retaining

| Capability | Current Source | Must Retain | Why It Still Matters | Suggested Next Handling |
| --- | --- | --- | --- | --- |
| MP4 upload API | `video_project/backend/app.py`, `video_project/app.py` | Yes | MP4 upload remains a formal requirement and supports the capture-analysis-demo story | Keep running as retained path first, then migrate by interface later |
| Video list API | `video_project/backend/app.py`, `video_project/app.py` | Yes | Teachers and demos still need to browse uploaded classroom media | Wrap or re-expose later from a unified teacher entry |
| Video stream / file access | `video_project/backend/app.py`, `video_project/app.py` | Yes | Essential for showing uploaded classroom recordings | Keep as retained path until a formal media service plan exists |
| Upload directory contract | `uploads/` runtime path | Yes | This is a live runtime asset tied to formal MP4 support | Preserve as runtime asset, do not Git-manage |
| Basic dashboard page idea | `video_project/frontend/src/views/Dashboard.vue` and old Flask dashboard stats | Yes, conceptually | The teacher still needs a visual summary entry | Rebuild on `cloud_backend`, do not reuse the mock-heavy old implementation directly |
| Video list page idea | `video_project/frontend/src/views/VideoList.vue` | Yes, conceptually | A video list remains useful in the final teacher-facing portal | Reuse the information architecture later, not the old code path directly |
| User/login model concept | `video_project/models.py`, old Flask login flow | Maybe later | Teacher-facing management may eventually need identity and auditability | Keep legacy for now; do not migrate until teacher portal scope is stable |
| System logs / operation audit idea | `SystemLog` in `models.py`, `/api/logs` in old app | Maybe | Future admin visibility may matter | Keep as legacy reference; do not migrate in current phase |

### Table 3: Capabilities Not Recommended For Continued Mainline Investment

| Capability | Current Source | Why Not Recommended For Mainline Investment | Legacy Only |
| --- | --- | --- | --- |
| Old Flask login page flow | `video_project/app.py`, `templates/login.html` | Tied to old page-oriented architecture, not part of the current cloud mainline | Yes |
| Old Flask video page | `video_project/app.py`, `templates/video.html` | Coupled to old login/session/video-streaming path | Yes |
| Old test video page | `templates/test_video.html` | Test artifact rather than a core teacher product path | Yes |
| Old MJPEG frame upload / live frame flow | `video_project/app.py` `/api/upload_frame`, `/video_feed` | Not aligned with current formal cloud boundary centered on result JSON and retained MP4 upload | Yes |
| Mock-heavy classroom stats API | `video_project/backend/app.py` `/api/dashboard/stats` | Uses random/mock data and does not reflect actual classroom interaction results | Yes |
| Old Flask session-auth mainline | `Flask-Login` path in `video_project/app.py` | Too tightly coupled to the old app shell and not yet needed for current minimal cloud dashboard | Yes |
| Old SQLite user/video/system-log schema as current mainline data layer | `instance/video.db`, `models.py` | Mixed concern set and not aligned with the new interaction-results-first data model | Yes |

## Coverage Mapping By Capability

### Already Covered By New Mainline

- interaction result ingestion
- result validation
- raw JSON landing
- latest result read-back
- minimal teacher-readable result dashboard

### Not Yet Covered But Worth Preserving

- MP4 upload
- video browsing / streaming
- future teacher identity and access control
- future operation/audit visibility

### Should Stay Legacy For Now

- old Flask pages
- old login/session shell
- old mock dashboard APIs
- old live frame upload and page-stream flow

## Integration Order Recommendation

### 1. Display-Layer Integration

Conclusion:

- the teacher should eventually see one main entry
- that entry should be the new dashboard/main portal direction, not the old Flask page system
- `cloud_backend` dashboard should become the unified display anchor

How MP4 and interaction results should relate at the display layer:

- classroom interaction results should remain the primary insight area
- MP4 should appear as a supporting media evidence/viewing module
- the teacher should not have to jump across unrelated app shells to connect “result” and “video”

Recommended display-layer order:

1. strengthen `cloud_backend` dashboard as the official teacher-facing entry
2. add recent results/history in the same display path
3. later add a video section or links that connect MP4 assets to classroom results

### 2. Interface-Layer Integration

Conclusion:

- interface-layer integration should come before code-layer integration
- the next formal candidates for gradual inclusion are MP4-related read/write interfaces
- old mock and page-driven interfaces should not be migrated as-is

What should gradually move toward the new mainline:

- MP4 upload endpoint behavior
- video list endpoint behavior
- video stream/read endpoint behavior

What may only need an adapter layer later:

- legacy upload path mapping
- legacy record lookup rules
- legacy teacher/session concepts if auth becomes necessary later

What should continue independently for now:

- old Flask page routes
- old session login routes
- live frame upload / streaming routes

### 3. Code-Layer Integration

Conclusion:

- now is not the right time for code-layer consolidation

Why not now:

- the current source repository only recently stabilized
- the new mainline is still defining its query and data model surface
- MP4-related retained functionality still sits in a different old code path
- direct code merging now would increase ambiguity faster than it creates value

Preconditions before code-layer integration becomes reasonable:

1. the new dashboard becomes the agreed teacher-facing entry
2. MP4-related retained interfaces are defined in the new interface boundary
3. history query and data model direction are stabilized
4. runtime/deploy boundaries remain safe and well documented

## Competition And Teacher-Facing View

### What Teachers / Judges Should Ultimately See

From a competition and classroom-demonstration standpoint, the strongest final presentation should center on:

- a unified dashboard home
- latest classroom interaction insight
- recent result history
- classroom participation / activity summary
- simple area or heat distribution view
- optional linked classroom video evidence

### Old Capabilities That Can Still Support The Demo

The old system still provides support value in these areas:

- MP4 upload and playback
- a “video list” mental model for teacher browsing
- a stored media path that can later support evidence playback

### What Should Not Steal The Main Story

The final demo should not be centered on:

- old Flask login pages
- old page routing shells
- mock dashboard metrics
- internal admin/session mechanics

The main story should remain:

1. classroom interaction results are produced
2. the cloud receives them
3. teachers can view them clearly
4. related classroom media can support interpretation

## Final Planning Conclusion

Recommended cloud-side integration sequence:

1. keep strengthening the new `cloud_backend` display and query surface
2. define formal retained MP4 interface requirements
3. integrate MP4 at the interface/display level
4. postpone code-level consolidation until the above boundaries are stable
