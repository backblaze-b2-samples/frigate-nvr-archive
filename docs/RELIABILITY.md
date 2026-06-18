<!-- last_verified: 2026-06-18 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies **both** B2 and Frigate connectivity and returns
  `healthy` or `degraded` (`b2_connected` + `frigate_connected` flags)
- Health endpoint is always available, even when B2 or Frigate is down
- The web app stays useful for browsing the existing archive even if Frigate is
  offline — only new ingest stops

## Continuous-write backpressure

- This is the highest sustained-write sample in the fleet — a multi-camera setup
  writes tens of GB/day to B2 indefinitely. Plan for it:
  - The archive worker is **single-writer** per index partition (read-modify-write
    of the day's JSONL is safe because only one worker appends). Do not run
    multiple workers against the same bucket prefix.
  - Polling (`ARCHIVE_POLL_INTERVAL_S`) bounds how far behind Frigate the archive
    can drift; if B2 or Frigate hiccups, the worker logs and retries on the next
    poll rather than crashing, and idempotent skip-by-id avoids double-writes.
  - A per-event failure is isolated: a not-yet-ready clip (404 or a transient 500
    while Frigate finalizes a just-ended event's recording) or a B2 error on one
    event is logged and skipped, never aborting the whole pass. The event is still
    indexed with whatever media did upload, so the index stays consistent.
  - For very high event rates, increase the interval and `archive_event_limit`
    together, and consider sharding by camera prefix across workers.
  - The on-demand UI sync is bounded by `ARCHIVE_SYNC_LIMIT` (default 5 new events
    per click) so the request returns promptly instead of grinding through a full
    window; the frontend also caps each request with a 60s client-side timeout.

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
