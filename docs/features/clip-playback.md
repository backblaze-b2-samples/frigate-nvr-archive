<!-- last_verified: 2026-06-18 -->
# Feature: Clip & snapshot playback from B2

## Purpose
Stream event clips and render snapshots directly from Backblaze B2 via short-lived
presigned URLs — no egress through a vendor cloud, no public bucket required.

## Used By
- UI: `components/events/event-detail-dialog.tsx` (video player + snapshot),
  `components/events/event-timeline.tsx` (snapshot thumbnails)
- API: presigned URLs embedded in `EventView`; `GET /events/{id}/clip` for download

## Core Functions
- `app/repo/archive_store.py` — `presign_get()` (inline playback), `presign_download()` (attachment)
- `app/service/events.py` — `_to_view()` attaches URLs; `clip_download_url()`

## Canonical Files
- Presign helpers: `services/api/app/repo/archive_store.py`
- Playback UI: `apps/web/src/components/events/event-detail-dialog.tsx`

## Inputs
- An event's `clip_key` / `snapshot_key` (B2 object keys recorded at archive time)

## Outputs
- Inline presigned GET URLs (10-min expiry) for `<video>` / `<img>` playback
- Forced-attachment presigned URL for "Download clip from B2"

## Flow
- Search/detail responses include `clip_url` + `snapshot_url` (presigned, 10 min)
- The browser plays the clip straight from B2 with the snapshot as the poster
- "Download clip from B2" hits `GET /events/{id}/clip` for a fresh attachment URL

## Edge Cases
- Event archived without a clip → snapshot shown instead; no player
- Event with neither → "No media archived for this event."
- Expired presigned URL → re-fetch the event to mint a fresh one

## UX States
- Snapshot-only events show the image; clip events show a play overlay on hover

## Verification
- Test files: `services/api/tests/test_events_search.py` (`test_views_carry_presigned_urls`)
- Required cases: views carry presigned URLs; download endpoint 404s when no clip
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: presigned URLs minted only for keys that exist on B2

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Event timeline & search](event-timeline.md)
- [docs/SECURITY.md](../SECURITY.md)
