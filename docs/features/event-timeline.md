<!-- last_verified: 2026-06-18 -->
# Feature: Event timeline & search

## Purpose
Let operators search the Frigate detection timeline ("all persons at the front
door this week") against a JSONL index stored in B2 — no database.

## Used By
- UI: `/events` page (`components/events/event-timeline.tsx`)
- API: `GET /events`, `GET /events/{id}`, `GET /events/{id}/clip`

## Core Functions
- `app/service/events.py` — `search_events()`, `get_event()`, `clip_download_url()`
- `app/repo/archive_store.py` — `read_index_range()`, `read_index_day()`, `presign_get()`
- `apps/web/src/lib/queries.ts` — `useEvents()`, `useEvent()`

## Canonical Files
- Search service: `services/api/app/service/events.py`
- Index store: `services/api/app/repo/archive_store.py`

## Inputs
- Filters (query params): `camera`, `label` (object class), `zone`, `start_date`,
  `end_date` (YYYY-MM-DD), `limit`

## Outputs
- `GET /events` → `EventView[]` (events + presigned snapshot/clip URLs), newest first
- `GET /events/{id}` → single `EventView`
- `GET /events/{id}/clip` → `{ url }` forced-attachment presigned download

## Flow
- Resolve the date range (default last 7 days, max 90)
- Load the JSONL index partitions for that range from B2
- Filter by camera / label / zone in memory
- Sort newest-first, cap to `limit`, attach short-lived presigned URLs

## Edge Cases
- Bad date string → 400 `EventError`
- `start_date` after `end_date` → 400
- Range wider than 90 days → 400
- No matching events → empty list (UI shows empty state)

## UX States
- Loading: skeleton grid
- Empty: "No events match" with hint to run the archive worker
- Error: inline `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_events_search.py`
- Required cases: filter by camera / label / zone; presigned URLs present; bad date 400
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: filters partition the sample events correctly; views carry URLs

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Clip & snapshot playback](clip-playback.md)
- [App Workflows](../app-workflows.md)
