<!-- last_verified: 2026-06-18 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/                /, /events, /upload, /archive, /files, /settings, /design
  src/components/events/       Event timeline, search filters, event detail
                          (clip playback), "Sync from Frigate" trigger
  src/components/archive/      Archive Library (scoped explorer): camera list +
                          per-date breakdown over the app's B2 prefix
  src/components/dashboard/    NVR stat cards, write-rate chart, recent-events
                          table, object-class breakdown
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/               b2_client + archive_store (B2, boto3);
                          frigate_client (Frigate HTTP API, httpx) — ALL
                          external systems live here
  app/service/            archive (Frigate -> B2 worker), events (timeline
                          search), stats (NVR dashboard), archive_browse
                          (scoped explorer), upload, metadata, files
  app/runtime/            events, archive, upload, files, health, metrics
  scripts/archive_worker.py    standalone Frigate -> B2 archive loop (CLI)
infra/frigate/     Real Frigate: docker-compose.yml + config.yml (the engine)
packages/shared/   Shared TypeScript types (EventView, NvrStats, …)
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

B2 is the **sole data store** — no DB, no queue. The searchable event index is a
set of JSONL objects on B2 (`<prefix>index/<YYYY-MM-DD>.jsonl`, one event per
line). See [ARCHITECTURE.md](ARCHITECTURE.md) for the data flow and B2 layout.

## 2. Building on This App

This app was scaffolded from the `vibe-coding-starter-kit`. The starter contract
below still holds — keep these pieces; the rest is this app's NVR archive.

**Keep as-is (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit the generated `components/ui/` files directly. Restyling happens through tokens in `globals.css`.
- **File Explorer.** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/` — the **full-bucket** browser. The Files sidebar entry stays. (Distinct from the scoped Archive Library.)
- **Upload.** `/upload` route, `apps/web/src/app/upload/`, and `apps/web/src/components/upload/` — here it imports an external clip/snapshot into this app's archive prefix on B2.
- The sidebar nav (Dashboard, Events, Upload, Archive, Files, Settings, plus the Design System utility link).

**This app's surface**
- **Events** (`/events`) — search the Frigate detection timeline (camera / object class / date / zone) over the JSONL index in B2; snapshots + clips play straight from B2 via presigned URLs. The "Sync from Frigate" button triggers a one-shot archive pass.
- **Archive Library** (`/archive`) — scoped explorer over this app's `frigate-nvr-archive/` prefix, grouped by camera and date (recordings / clips / snapshots). Required sample-specific explorer, distinct from the full-bucket `/files`.
- **NVR Dashboard** (`/`) — cameras, events today, footage archived to B2 (GB), today's write volume, the daily write-rate chart, object-class mix, recent events. New aggregations flow `runtime -> service -> repo` and are exposed via TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare `useEffect + fetch`.

**Vendor-fidelity invariant (non-negotiable)**
- **Frigate is the engine.** Detection is performed by **real Frigate**, never
  re-implemented here. Our Python has **no** `ultralytics`/YOLO/torch. The only
  way we touch Frigate is the `repo/frigate_client.py` adapter, which consumes
  Frigate's documented HTTP API (`/api/events`, clips, snapshots) over `httpx`.
- The primary feature — the archive worker that ships Frigate events + media to
  B2 and writes the searchable index — must stay **real**: real Frigate calls,
  real B2 objects. No mocked events, synthetic clips, or placeholder index
  entries. B2 credentials are the only secret; Frigate runs keyless.

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external systems wrapped in `repo/` adapters (`b2_client`, `archive_store`, `frigate_client`)
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

`repo/frigate_client.py` is a `repo/` adapter that uses `httpx` (not boto3) to
talk to Frigate — the boto3-containment test does not apply to it, but the
layering rules do: nothing outside `repo/` may import `httpx` or `boto3`.

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch`. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Frigate (the engine) + archive worker
docker compose -f infra/frigate/docker-compose.yml up   # real Frigate on :5000
python services/api/scripts/archive_worker.py           # Frigate -> B2 archive loop

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
