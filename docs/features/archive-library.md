<!-- last_verified: 2026-06-18 -->
# Feature: Archive Library (scoped explorer)

## Purpose
Browse this app's own archive on B2 — grouped by camera and date — without
exposing the whole bucket. The required sample-specific explorer, distinct from
the full-bucket File Browser.

## Used By
- UI: `/archive` page (`components/archive/archive-library.tsx`, `camera-dates.tsx`)
- API: `GET /archive`, `GET /archive/cameras/{camera}/dates`

## Core Functions
- `app/service/archive_browse.py` — `get_overview()`, `list_cameras()`, `list_camera_dates()`
- `app/repo/archive_store.py` — `list_objects()` (scoped), `list_index_days()`, `read_index_day()`
- `apps/web/src/lib/queries.ts` — `useArchiveOverview()`, `useArchiveCameraDates()`

## Canonical Files
- Browse service: `services/api/app/service/archive_browse.py`
- Explorer UI: `apps/web/src/components/archive/archive-library.tsx`

## Inputs
- None for the overview; a camera name for the per-date breakdown

## Outputs
- `GET /archive` → `{ prefix, cameras[] }` with per-camera object/byte/clip/snapshot/recording counts
- `GET /archive/cameras/{camera}/dates` → `ArchiveDate[]` (date, objects, bytes)

## Flow
- List `list_objects_v2` over the scoped `frigate-nvr-archive/` prefix only
- Classify each key into camera + kind (clip / snapshot / recording)
- Roll up per camera; expand a camera to see its per-date object/byte totals
  (recording day folders + event days inferred from the JSONL index)

## Edge Cases
- Empty archive → empty state with hint to run the worker
- Camera with only events (no recordings) → dates come from the index
- Scope guard: the browse never lists outside the archive prefix

## UX States
- Loading: skeleton rows
- Empty: "Nothing archived yet"
- Loaded: collapsible camera rows with date breakdowns

## Verification
- Test files: covered indirectly via `archive_store` list/scope behavior;
  add cases in `services/api/tests/` when extending grouping logic
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: only objects under `frigate-nvr-archive/` ever appear here

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Browser](file-browser.md) (full-bucket counterpart)
- [App Workflows](../app-workflows.md)
