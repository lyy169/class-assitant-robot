# Cloud Storage Repository V1

## 1. Goal

The cloud backend needs a formal storage abstraction that can evolve beyond file-only queries while keeping the current API stable.

This iteration introduces:

- a repository interface for query and indexing operations
- continued raw JSON file persistence as the write safety baseline
- a minimal SQLite-backed implementation for recent/latest queries

This iteration does not change public API routes.

## 2. Storage Layers

The storage layer is split into two responsibilities.

### 2.1 Raw File Persistence

Raw file persistence remains mandatory.

Purpose:

- keep the full uploaded V1.1 payload as source of truth
- preserve a simple recovery path even if SQLite indexing fails
- keep current operational behavior compatible with the existing raw-first model

### 2.2 Repository Query Abstraction

The repository abstraction is responsible for query and indexing behavior.

Purpose:

- unify latest/recent/detail style lookups behind one interface
- allow switching query source without changing API handlers
- support SQLite-backed formalization while keeping file fallback

## 3. Repository Interface Responsibilities

The repository interface in this iteration should support:

- `save`
  - index a validated payload after raw file persistence succeeds
- `latest`
  - return the latest result, optionally filtered by `classroom_id`
- `recent`
  - return recent results, optionally filtered by `classroom_id`
- `detail`
  - optional in this round if low-cost, keyed by `analysis_id`

The interface is not responsible for:

- schema validation
- HTTP response formatting
- dashboard rendering

## 4. FileRepository Retention

`FileRepository` remains necessary in this round.

Retention reasons:

- raw JSON is still the operational source of truth
- file reads remain the lowest-risk fallback
- sample/fallback behavior already depends on file-based lookup
- SQLite must not become a hard dependency for ingestion success

Expected role after this iteration:

- always write raw JSON
- remain available as fallback query source

## 5. SQLiteRepository Addition

`SQLiteRepository` is added as a minimal formal query/index backend.

Initial responsibilities:

- create a SQLite database file if missing
- create the minimal result index table
- store a normalized summary row for each uploaded payload
- serve `latest` and `recent` queries from SQLite when enabled
- optionally serve `detail` by `analysis_id`

This iteration does not require full payload decomposition into multiple relational tables.

## 6. Query Scope In This Round

This round should support:

- `save`
- `latest`
- `recent`

Optional if low-cost:

- `detail` by `analysis_id`

This round does not require:

- trend aggregation
- pagination
- advanced joins

## 7. Raw Safety Strategy

Raw JSON write remains the mandatory first durable step.

Required behavior:

1. validate V1.1 payload
2. write raw JSON to `cloud_backend/data/raw/YYYY-MM-DD/<analysis_id>.json`
3. index that payload into SQLite
4. if SQLite indexing fails, raw JSON must still remain on disk

Query behavior:

- when SQLite is enabled and healthy, latest/recent should prefer SQLite
- when SQLite is disabled or unavailable, the system must still be able to fall back to file-based querying

## 8. Backend Selection

The cloud backend should be able to choose query storage mode without changing API handlers.

Expected modes in this round:

- `file`
- `sqlite`

The write path still keeps raw JSON in both modes.

## 9. Out Of Scope

This round explicitly does not do:

- PostgreSQL
- large-scale data migration
- route renaming
- dashboard redesign
- schema expansion
- removal of file fallback
