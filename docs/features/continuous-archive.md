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
- Frigate offline → `list_events` raises `RuntimeError`; worker logs and keeps polling (API returns 502)
- Event clip/snapshot not ready (404 **or** a transient 500 while Frigate is still
  finalizing the recording segment) → that artifact is skipped and logged; the
  event is still archived with whatever media came back (`has_clip=false` when the
  clip was skipped), so the index entry stays consistent and the pass continues
- A failure archiving one event (e.g. a B2 hiccup) → logged and skipped; the rest
  of the pass still completes
- Duplicate event id in a re-poll → skipped (already indexed)
- Malformed Frigate event → skipped with a warning

## On-demand sync (UI button)
- `POST /events/archive` passes `max_new=ARCHIVE_SYNC_LIMIT` (default 5) so a
  single "Sync from Frigate" click archives at most a few new events and returns
  in seconds (a full 50-event window of fresh clips would take minutes). Repeated
  clicks drain any remaining backlog; the standing worker keeps the full window
  current in the background.

## UX States
- Events page "Sync from Frigate" button: idle / syncing (spinner) / toast result
- The frontend `apiFetch` bounds every request with a 60s `AbortController`
  timeout, so the button surfaces a "Request timed out" error rather than
  spinning forever if a request ever stalls

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
