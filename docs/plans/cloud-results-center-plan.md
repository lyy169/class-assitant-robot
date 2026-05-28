# Cloud Results Center Plan

## Position

This round upgrades `cloud_backend/` from a latest-result viewer to a minimal teacher-facing results center.

The goal is not a full frontend rewrite. The goal is to make the cloud mainline readable, filterable, and extensible for later database and dashboard work.

## Query Capability Map

### Latest Query

- route: `GET /api/latest-interaction-result`
- supports optional `classroom_id`
- returns the latest matching result
- still uses file-backed JSON lookup

### Recent Query

- route: `GET /api/recent-interaction-results`
- default limit: 5
- accepts `limit`
- sorts in reverse chronological order
- returns `source_kind`, `source_path`, `summary`, and raw `result`

### Classroom Filter

- query parameter: `classroom_id`
- available on:
  - `GET /api/latest-interaction-result`
  - `GET /api/recent-interaction-results`
  - `GET /dashboard`
- current behavior is file-backed and exact-match based
- future database filtering can remain API-compatible while becoming more complete

## Dashboard Module Structure

Current `/dashboard` modules:

1. classroom overview card
   - latest classroom
   - source host
   - total events
   - participation
2. recent result list
   - time window
   - classroom
   - total events
   - participation
   - source kind
3. classroom filter entry
   - simple query-parameter form
4. region / heat summary
   - readable ranked text summary
5. latest interaction breakdown
   - count list for the latest result
6. system note
   - explains that MP4 and video archive remain future supporting modules

## Teacher-Facing Required Fields

The dashboard currently depends on these fields being present or derivable:

- `window_id`
- `classroom_id`
- `source_host`
- `started_at`
- `ended_at`
- `generated_at`
- `interaction_counts.total_events` or derivable event counts
- `interaction_counts.participants`
- `interaction_counts.total_students` or `meta.total_students`
- `grid_stats`

## Current File Storage Limitations

- filtering scans files instead of indexed records
- sorting relies on payload time fields and file metadata
- no historical trend aggregation
- no result-detail route by `window_id`
- no pagination
- no durable relation to MP4 or video archive data yet

## Database Expansion Path

The next storage upgrade should preserve the current route contract:

1. keep raw JSON ingestion unchanged
2. mirror raw payloads into a structured table
3. move recent-query and classroom filtering into database-backed repository methods
4. add result detail, trends, and joined video archive metadata later

## Future MP4 / Video Integration

MP4 upload and video browsing remain preserved capabilities but are not merged in this round.

Planned role in the unified teacher entry:

- dashboard stays the top-level classroom results center
- future result detail pages can link to related MP4 or video archive records
- old video pages are treated as supporting views, not the primary teacher entry

## Recommended Next Development Order

1. add recent result detail by `window_id`
2. add pagination and stronger classroom filtering
3. add database-backed repository implementation
4. add MP4 / video archive linkage from teacher-facing detail pages
