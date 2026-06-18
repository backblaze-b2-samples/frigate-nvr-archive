<!-- last_verified: 2026-06-18 -->
# Architecture

Frigate NVR Archive is a B2 archive + search + playback layer on top of a real
**Frigate** NVR. Frigate is the detection engine; this app ships its media and a
searchable detection index to Backblaze B2 and serves them back.

## Components

- **infra/frigate/** — a **real Frigate** instance (`docker-compose.yml` + `config.yml`).
  Ingests an RTSP/file camera stream, runs local object detection, and exposes
  recordings, event clips, and snapshots on its HTTP API at `:5000`. This is the
  engine — detection is never re-implemented in our code.
- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - NVR Dashboard: cameras, events today, footage archived, write-rate chart, object-class mix
  - Events: search the detection timeline (camera / object class / date / zone), play clips from B2
  - Archive Library: scoped explorer over the app's own B2 prefix, grouped by camera + date
  - File Browser (full bucket), clip Upload, dark mode
- **services/api/** — FastAPI backend (layered architecture)
  - Archive worker: Frigate events + media -> B2 + JSONL detection index
  - Event timeline search over the JSONL index in B2 (presigned playback URLs)
  - NVR dashboard aggregation; scoped Archive Library browse
  - Health check (B2 + Frigate connectivity), JSON logging, Prometheus metrics
  - `scripts/archive_worker.py` — standalone CLI for the Frigate -> B2 loop
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access: b2_client + archive_store (boto3 B2), frigate_client (httpx)
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only in `repo/`. `httpx` (the Frigate client) only in `repo/` too.
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (event.py, files.py, stats.py, …)
    config/                Settings loaded from environment
    repo/                  b2_client, archive_store (B2); frigate_client (Frigate API)
    service/               archive, events, stats, archive_browse, upload, metadata, files
    runtime/               events, archive, upload, files, health, metrics
  scripts/archive_worker.py    Frigate -> B2 archive loop (CLI)
  tests/                   pytest tests (structural + unit + integration)
```

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API). The **sole data store** —
  no application database, no queue. All media and the searchable event index
  live under the `frigate-nvr-archive/` prefix.

### B2 object layout (scoped to `frigate-nvr-archive/`)

```
recordings/<camera>/<YYYY-MM-DD>/<HH>/<segment>.mp4
events/<camera>/<event_id>/clip.mp4
events/<camera>/<event_id>/snapshot.jpg
index/<YYYY-MM-DD>.jsonl        # one detection event per line (searchable)
index/cameras.json              # camera registry + last-seen summary
imports/<filename>              # clips imported via the Upload page
```

The JSONL index **is** the search backend: `service/events.py` loads the
partitions for the queried date range from B2 and filters them in memory. B2 has
no native append, so the archive worker read-modify-writes the day partition; the
worker is single-writer, which is safe at the sample's scale.

## External Services

- **Frigate HTTP API** (`:5000`) — `/api/events`, `/api/events/<id>/clip.mp4`,
  `/api/events/<id>/snapshot.jpg`, `/api/version`. Consumed by
  `repo/frigate_client.py` via `httpx`. Frigate runs keyless.
- **Backblaze B2 S3 API** — put/list/head/delete + presigned URLs via `boto3`.

## Boundary Invariants

- **No external SDK leakage**: `boto3` and `httpx` are imported only in `app/repo/`.
- **Vendor fidelity**: no `ultralytics`/YOLO/torch anywhere — Frigate does detection.
- **No raw dicts at boundaries**: typed Pydantic models cross every layer boundary.
- **No mutable globals**: configuration is read-only after init.
- **Scoped deletes**: `archive_store.delete_prefix` refuses any prefix outside
  `frigate-nvr-archive/`, so retention cleanup can never touch other apps' data.
- **Validated inputs**: HTTP inputs validated by FastAPI/Pydantic; file keys
  validated against path-traversal patterns.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> Frigate** — same-host/LAN HTTP; treat Frigate as trusted infra (no auth by default)
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — short-lived presigned URLs for clip/snapshot playback (10-min expiry)

## Data Flows

- **Archive** (primary): worker polls `Frigate /api/events` -> downloads clip +
  snapshot -> `repo/archive_store` writes both to B2 -> appends the event to the
  day's `index/*.jsonl` -> updates `index/cameras.json`.
- **Search**: Browser -> `GET /events?camera&label&zone&start_date&end_date` ->
  service loads the JSONL partitions for the range from B2, filters, and returns
  events with presigned snapshot + clip URLs.
- **Playback**: Browser plays the presigned clip/snapshot URL straight from B2;
  `GET /events/{id}/clip` returns a forced-attachment presigned download URL.
- **Dashboard**: Browser -> `GET /events/stats` + `/events/stats/write-volume` ->
  service rolls the recent index partitions into headline metrics.
- **Archive Library**: Browser -> `GET /archive` + `/archive/cameras/{cam}/dates`
  -> service lists `list_objects_v2` over the scoped prefix, grouped by camera/date.
- **Upload**: Browser -> `POST /upload` -> validates clip/snapshot -> writes under
  `frigate-nvr-archive/imports/`.

## Deployment

- **Local dev** — `pnpm dev` runs web + API via `concurrently`; Frigate runs in
  Docker (`infra/frigate/`); the archive worker runs as a separate process.
- **Railway** — see `infra/railway/README.md`.

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware
- `/metrics` endpoint (Prometheus format)
- `/health` endpoint (B2 + Frigate connectivity)

## Canonical Files

- Archive worker (service): `services/api/app/service/archive.py`
- Frigate adapter: `services/api/app/repo/frigate_client.py`
- B2 archive store: `services/api/app/repo/archive_store.py`
- Event search: `services/api/app/service/events.py`
- Pydantic models: `services/api/app/types/event.py`
- Config: `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Continuous archive to B2](docs/features/continuous-archive.md)
- [Event timeline & search](docs/features/event-timeline.md)
- [Clip & snapshot playback](docs/features/clip-playback.md)
- [Archive Library](docs/features/archive-library.md)
- [NVR Dashboard](docs/features/dashboard.md)
- [File Browser](docs/features/file-browser.md) · [Clip Upload](docs/features/file-upload.md) · [Snapshot metadata](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
