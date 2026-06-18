<!-- last_verified: 2026-06-18 -->
# Security

Security principles and implementation for the frigate-nvr-archive.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> Frigate**: HTTP over the same host / LAN. Frigate ships with no auth by
  default, so it is treated as **trusted infrastructure** — keep it off the public
  internet (bind it to localhost / a private network, or front it with auth). The
  archive worker only *reads* Frigate; it never mutates it.
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **Client -> B2**: Short-lived presigned URLs for clip/snapshot playback (10-min
  expiry). Inline-playback URLs render media; the per-event clip *download*
  endpoint forces `Content-Disposition: attachment`.

## Upload Validation (clip import)

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (500MB default)
- Content-type allowlist (surveillance media only: mp4/mov/jpg/png/webp)
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The bucket is the only access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads
- **Scoped deletes**: `repo/archive_store.delete_prefix` refuses any prefix that
  is not under `frigate-nvr-archive/`, so retention cleanup can never delete
  another app's data even if called with a bad prefix

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
