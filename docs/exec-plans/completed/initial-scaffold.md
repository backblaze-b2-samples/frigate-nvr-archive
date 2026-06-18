# Build plan — `frigate-nvr-archive`

Source of truth: `.claude/scratch/vcsk-7226d5f0-f65e-48e6-95f5-cc6498dce6e8/` (fresh clone of `vibe-coding-starter-kit`).
Pattern reference: the shipped `yolo11-batch-detection-pipeline` sample (same starter lineage).

## 1. Purpose

`frigate-nvr-archive` is a B2 sample for home / small-business security operators who run a
self-hosted NVR with **[Frigate](https://github.com/blakeblackshear/frigate)**. Frigate ingests
continuous RTSP/CCTV streams, runs **local object detection**, and produces recording segments,
event clips, and detection snapshots. This sample is the **B2 archive + search layer** on top of
Frigate: a worker ships Frigate's media and detection metadata to Backblaze B2 in real time, and a
web app lets operators **search the event timeline** ("all persons at the front door this week") and
**play clips straight from B2**. The pitch: months of affordable surveillance footage on B2 instead
of a vendor cloud subscription — and the highest sustained write rate of any sample in the fleet
(a 4-camera @ 1 Mbps setup writes ~43 GB/day to B2 indefinitely).

**Vendor-fidelity decision (non-negotiable):** Frigate is the engine. Detection is done **by real
Frigate**, never re-implemented in our Python. Our code is strictly the B2 archive + search +
playback layer that consumes Frigate's HTTP API (`/api/events`, `/api/events/<id>/clip.mp4`,
`/api/events/<id>/snapshot.jpg`, recordings VOD). No `ultralytics`/YOLO model runs in our service.
(Cf. the "sample vendor fidelity" rule: a sample themed on a vendor uses that vendor's own engine.)

## 2. Architecture delta from `vibe-coding-starter-kit`

| **Keep (as-is / light rename only)** | **Trim (remove from starter)** | **Add (new for frigate-nvr-archive)** |
|---|---|---|
| Monorepo layout: `apps/web` (Next 16) + `services/api` (FastAPI layered) + `packages/shared` | `docs/exec-plans/completed/2026-02-*.md` (starter history) | **Frigate engine** — `infra/frigate/` with `docker-compose.yml` + `config.yml` running **real Frigate**; camera input via env (looped file or user RTSP), detects person/car/etc., records + clips + snapshots, API on :5000 |
| Whole UI kit `components/ui/`, design tokens `globals.css`, `/design` page | starter `docs/images/*.png` (binary; sample-4 re-adds) | **Archive worker** — `services/api/app/service/archive.py` + `repo/frigate_client.py` (HTTP to Frigate) + CLI `scripts/archive_worker.py`: poll Frigate events -> download media -> upload to B2 -> write event index to B2 |
| **File Explorer** `/files` (full-bucket browse) — *non-negotiable keep* | `docs/features/metadata-extraction.md` kept but reframed (snapshot image metadata; drop PDF wording) | **Event timeline + search** — route `/events`, `components/events/`, `runtime/events.py`, `service/events.py`, `types/event.py`: filter by camera / object class / date / zone; thumbnails + clip playback via presigned URLs |
| **Upload** `/upload` (kept per contract; reframed as "import an external clip into the archive") | (no other deletions) | **Archive Library (scoped explorer)** — route `/archive`, `components/archive/`, `runtime/archive.py`, `service/archive_browse.py`: browse **only** `frigate-nvr-archive/` prefix, grouped by camera/date (recordings / clips / snapshots). Required sample-specific explorer, distinct from full-bucket `/files`. |
| FastAPI layering `types->config->repo->service->runtime`, structural tests, `/health`, `/metrics`, JSON logging | | **NVR Dashboard** — adapt `/` + `components/dashboard/`: stat cards (cameras, events today, footage archived to B2 GB, today's write volume), write-rate chart, recent-events table, object-class breakdown |
| `scripts/doctor.mjs`, `scripts/dev.sh`, `scripts/pick-port.mjs`, Railway infra (rename only) | | New B2/Frigate settings: `frigate_url`, `frigate_rtsp_input`, `archive_prefix="frigate-nvr-archive/"`, `archive_poll_interval_s` |
| TanStack Query data layer (`lib/queries.ts`, `lib/api-client.ts`) | | New feature docs (see section 5) + adapted README/ARCHITECTURE/AGENTS/app-workflows |

Sidebar nav after change: **Dashboard / Events / Upload / Archive / Files / Settings** + Design (util).
(Mirrors yolo11's Dashboard-Upload-Runs-Files-Settings; "Events" = primary, "Archive" = scoped explorer.)

## 3. B2 surface (S3-compatible only — no b2-native)

All via `boto3` in `repo/` with `user_agent_extra="b2ai-frigate-nvr-archive"`, signature v4.

| Op | Used for |
|---|---|
| `put_object` | recording segments, event clips, snapshots, and the JSONL event index |
| `list_objects_v2` (paginated) | dashboard stats, timeline build, Archive Library (scoped prefix), Files (full bucket) |
| `head_object` | object metadata / existence checks |
| `generate_presigned_url` | clip + snapshot playback/download (10-min expiry, forced attachment for downloads) |
| `delete_object` | retention cleanup — **always scoped to `frigate-nvr-archive/`** prefix |

No b2-native API anywhere. **No external API provider / no second API key** — detection runs locally
in Frigate (keyless OSS). Only B2 credentials are required. (`api-provider-selection.md` not needed.)

### B2 object layout (scoped to `frigate-nvr-archive/`)
```
frigate-nvr-archive/
  recordings/<camera>/<YYYY-MM-DD>/<HH>/<segment>.mp4
  events/<camera>/<event_id>/clip.mp4
  events/<camera>/<event_id>/snapshot.jpg
  index/<YYYY-MM-DD>.jsonl        # one detection event per line (searchable index)
  index/cameras.json              # camera registry + last-seen summary
```
Search = service loads the JSONL index partitions for the queried date range from B2 and filters by
camera/label/zone/time, then returns events with presigned snapshot+clip URLs. **B2 is the sole data
store — no application database** (preserves the starter invariant).

## 4. Key features (seed README list + docs/features/* stubs)

1. **Continuous archive to B2** (`continuous-archive.md`) — archive worker streams Frigate recording
   segments, event clips, and snapshots to B2 in real time; emphasize sustained write rate.
2. **Event timeline & search** (`event-timeline.md`) — searchable JSONL event index in B2; filter by
   camera / object class / date / zone ("all persons at the front door this week").
3. **Clip & snapshot playback from B2** (`clip-playback.md`) — presigned-URL streaming of clips and
   snapshots directly from B2, no egress through a vendor cloud.
4. **Archive Library (scoped explorer)** (`archive-library.md`) — browse the sample's own
   `frigate-nvr-archive/` prefix by camera + date.
5. **NVR Dashboard** (`dashboard.md`, rewritten) — cameras, events today, footage archived (GB),
   write-rate, object-class mix.
6. **Kept B2 scaffolding** — File Browser (full bucket), Upload, snapshot metadata extraction.

## 5. Doc transforms

- **Rewrite:** `README.md`, `ARCHITECTURE.md`, `AGENTS.md` (rename + new screens + Frigate engine +
  archive worker + index store), `docs/app-workflows.md` (Ingest->Detect->Clip->Index->Query),
  `docs/features/dashboard.md` (-> NVR dashboard).
- **Light edit (keep):** `docs/features/file-browser.md`, `docs/features/file-upload.md`,
  `docs/features/metadata-extraction.md` (snapshot image metadata; drop PDF), `docs/dev-workflows.md`
  (commands/slug), `docs/SECURITY.md` (add Frigate trust boundary + presigned clips),
  `docs/RELIABILITY.md` (continuous-write backpressure note).
- **New stubs:** `docs/features/continuous-archive.md`, `event-timeline.md`, `clip-playback.md`,
  `archive-library.md` (use `docs/features/_template.md`).
- **Delete:** starter `docs/exec-plans/completed/2026-02-*.md`, starter `docs/images/*.png`.
- **Add:** this plan lands at `docs/exec-plans/completed/initial-scaffold.md` in Phase 5.

## 6. Rename table (`vibe-coding-starter-kit` -> `frigate-nvr-archive`)

| Scope | From | To |
|---|---|---|
| Repo / kebab slug | `vibe-coding-starter-kit` | `frigate-nvr-archive` |
| Title Case | Vibe Coding Starter Kit | Frigate NVR Archive |
| Root npm pkg | `vibe-coding-starter-kit` | `frigate-nvr-archive` |
| Web pkg | `@vibe-coding-starter-kit/web` | `@frigate-nvr-archive/web` |
| Shared pkg | `@vibe-coding-starter-kit/shared` | `@frigate-nvr-archive/shared` |
| pnpm filters (root package.json scripts) | `@vibe-coding-starter-kit/web` | `@frigate-nvr-archive/web` |
| S3 `user_agent_extra` | `b2ai-oss-start` | `b2ai-frigate-nvr-archive` |
| UTM `utm_content` (all README/sidebar links) | `b2ai-oss-start` | `b2ai-frigate-nvr-archive` |
| B2 prefix / settings `archive_prefix` | (n/a) | `frigate-nvr-archive/` |
| Env var | `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| Env var | (add) | `B2_REGION` |
| Env var | (add) | `B2_PUBLIC_URL` (optional public base; else presigned) |
| New Frigate env | (n/a) | `FRIGATE_URL`, `FRIGATE_RTSP_INPUT`, `ARCHIVE_POLL_INTERVAL_S` |
| Railway docs env table | `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` (+ `B2_REGION`) |

Standard B2_* env names (CLAUDE.md Standard #3) — match the shipped fleet exactly:
`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, `B2_ENDPOINT`,
`B2_PUBLIC_URL` (the b2-doctor skill is stale on `B2_KEY_ID`/`B2_PUBLIC_URL_BASE`; follow the fleet).

## Run / demo flow
1. `pnpm install` + Python venv + `pip install -r services/api/requirements.txt`.
2. `cp .env.example .env`, fill B2 creds + `FRIGATE_URL`.
3. Live mode: `docker compose -f infra/frigate/docker-compose.yml up` -> real Frigate with the
   configured camera input; then run the archive worker -> media + index land in B2.
4. `pnpm dev` -> web app reads from B2: Dashboard, Events search, Archive Library, Files.
