<!-- last_verified: 2026-06-18 -->
# App Workflows

User journeys inside the application. The end-to-end pipeline is
**Ingest → Detect → Clip → Index → Query**.

## The pipeline (Ingest → Detect → Clip → Index → Query)

- **Ingest**: Frigate (`infra/frigate/`) pulls a camera's RTSP/file stream.
- **Detect**: Frigate runs local object detection and records clips + snapshots.
- **Clip + Index**: the archive worker (`services/api/scripts/archive_worker.py`)
  pulls each event from Frigate's API, ships the clip + snapshot to B2, and
  appends the event to the day's JSONL index in B2.
- **Query**: the web app reads the index from B2 to power Dashboard, Events
  search, and the Archive Library — and streams clips back via presigned URLs.
- See: [Continuous archive to B2](features/continuous-archive.md)

## Search the Event Timeline

- User navigates to `/events`
- Picks filters: camera, object class, date range (zone optional)
- The API loads the JSONL index partitions for the range from B2 and filters them
- Matching events render as cards with snapshot thumbnails (newest first)
- Click a card → detail dialog plays the clip straight from B2; download is one click
- "Sync from Frigate" triggers a one-shot archive pass and refreshes the timeline
- Empty state: "No events match" with a hint to run the archive worker
- See: [Event timeline & search](features/event-timeline.md), [Clip & snapshot playback](features/clip-playback.md)

## Browse the Archive Library (scoped)

- User navigates to `/archive`
- Sees cameras rolled up from this app's `frigate-nvr-archive/` prefix on B2
- Expands a camera to see per-date object + byte totals (recordings + events)
- Distinct from the full-bucket Files explorer — this is only the app's prefix
- See: [Archive Library](features/archive-library.md)

## Import a Clip

- User navigates to `/upload`
- Drops or selects a clip/snapshot (footage from another NVR, a phone, etc.)
- Client validates file size (max 500MB) and type (clips/snapshots only)
- On success it lands under `frigate-nvr-archive/imports/` and appears in the Archive Library
- See: [Clip Upload](features/file-upload.md)

## Browse and Manage Files (full bucket)

- User navigates to `/files`
- Page loads the full bucket's file list (sorted most recent first), tree view
- Hover a row for preview / download / delete; preview shows image + metadata
- Empty bucket shows "No files found"
- See: [File Browser](features/file-browser.md)

## View the NVR Dashboard

- User navigates to `/` (home)
- Two parallel API calls load: NVR stats and the daily write volume
- Stat cards: cameras, events today, footage archived to B2, written today
- Write-rate chart: MB written to B2 per day (last 7 days)
- Object-class breakdown + recent-events table
- Empty state: "No footage archived yet"
- See: [NVR Dashboard](features/dashboard.md)
