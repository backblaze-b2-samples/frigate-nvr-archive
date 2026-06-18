<!-- last_verified: 2026-06-18 -->
# Feature: NVR Dashboard

## Purpose
Give an at-a-glance overview of the surveillance archive: cameras, detection
events, footage written to B2, and the daily write rate — the strategic B2 story.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /events/stats`, `GET /events/stats/write-volume`

## Core Functions
- `apps/web/src/components/dashboard/nvr-stats-cards.tsx` — 4 stat cards
- `apps/web/src/components/dashboard/write-volume-chart.tsx` — bytes written per day
- `apps/web/src/components/dashboard/object-class-breakdown.tsx` — object-class mix
- `apps/web/src/components/dashboard/recent-events-table.tsx` — recent events
- `services/api/app/service/stats.py` — `get_nvr_stats()`, `get_write_volume()`
- `services/api/app/repo/archive_store.py` — `read_index_range()` data access

## Canonical Files
- Dashboard aggregation: `services/api/app/service/stats.py`
- Stat cards: `apps/web/src/components/dashboard/nvr-stats-cards.tsx`

## Inputs
- None (dashboard loads data automatically; scans the last 30 days of index)

## Outputs
- `GET /events/stats` → `NvrStats` (cameras, events_total, events_today,
  footage_bytes(+human), bytes_today(+human), label_counts, camera_summaries, recent_events)
- `GET /events/stats/write-volume?days=7` → `DailyWriteVolume[]` for the write-rate chart

## Flow
- Page loads → two parallel API calls (stats, write volume)
- Stat cards: cameras, events today, footage archived to B2, written today
- Write-rate chart: MB written to B2 per day (last 7 days)
- Object-class breakdown: relative bars per detected label
- Recent-events table: last 10 events (object, camera, score, when)

## Edge Cases
- API unavailable → inline `ErrorState` instead of misleading zeros
- Nothing archived yet → empty chart/table with a hint to run the worker
- Many index partitions → dashboard scans only the last 30 days to stay bounded

## UX States
- Loading: skeleton placeholders for cards, chart, table
- Empty: "No footage archived yet" / "No events yet"
- Loaded: populated cards, chart, breakdown, table

## Verification
- Test files: aggregation exercised via `services/api/tests/` index reads;
  extend with cases when adding new metrics
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: metrics roll up the JSONL index correctly; no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Continuous archive to B2](continuous-archive.md)
- [App Workflows](../app-workflows.md)
