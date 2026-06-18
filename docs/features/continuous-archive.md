<!-- last_verified: 2026-06-18 -->
# Feature: Continuous archive to B2

## Purpose
Stream a real Frigate NVR's detection events and media (clips, snapshots) to
Backblaze B2 in real time, so months of footage live affordably on B2 instead of
a vendor cloud — the highest sustained write rate of any sample in the fleet.

## Used By
- Job: `services/api/scripts/archive_worker.py` (CLI loop)
- API: `POST /events/archive` (on-demand one-shot sync; "Sync from Frigate" button)

## Core Functions
- `app/service/archive.py` — `archive_recent()`, `archive_event()` (the worker)
- `app/repo/frigate_client.py` — `list_events()`, `download_clip()`, `download_snapshot()`
- `app/repo/archive_store.py` — `put_bytes()`, `append_event()`, `write_cameras()`

## Canonical Files
- Worker orchestration: `services/api/app/service/archive.py`
- Frigate adapter: `services/api/app/repo/frigate_client.py`

## Inputs
- Frigate events: dicts from `GET /api/events` (Frigate API)
- Media: `clip.mp4` / `snapshot.jpg` bytes from Frigate per event

## Outputs
- B2 objects: `events/<camera>/<id>/clip.mp4`, `.../snapshot.jpg`
- B2 index line appended to `index/<YYYY-MM-DD>.jsonl`
- `index/cameras.json` updated with last-seen per camera
- Side effect: none beyond B2 (no DB)

## Flow
- Poll Frigate for recently-ended events (`after` cursor avoids re-reads)
- Skip events already present in the day's JSONL index (idempotent re-poll)
- For each new event: download clip + snapshot, upload both to B2
- Append the event record (with B2 keys + byte sizes) to the day's index
- Loop every `ARCHIVE_POLL_INTERVAL_S` seconds (or `--once` for a single pass)

## Edge Cases
- Frigate offline → `RuntimeError`; worker logs and keeps polling (API returns 502)
- Event has no clip/snapshot (404 from Frigate) → archived with `has_clip=false`
- Duplicate event id in a re-poll → skipped (already indexed)
- Malformed Frigate event → skipped with a warning

## UX States
- Events page "Sync from Frigate" button: idle / syncing (spinner) / toast result

## Verification
- Test files: `services/api/tests/test_archive_worker.py`
- Required cases: ships media + indexes; skips already-indexed; skips malformed
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: media lands under the archive prefix on B2; one index line per event

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Event timeline & search](event-timeline.md)
- [App Workflows](../app-workflows.md)
