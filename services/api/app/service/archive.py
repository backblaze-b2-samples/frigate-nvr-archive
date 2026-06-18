"""Archive worker: ship real Frigate detection events + media to Backblaze B2.

This is the primary feature. For every recently-ended Frigate event it:
  1. downloads the event's clip + snapshot from Frigate (the engine),
  2. uploads both to B2 under the archive prefix, and
  3. appends a searchable record to the day's JSONL index in B2.

Detection itself is done by Frigate — this module never runs a model. It only
orchestrates plain Pydantic models (`ArchiveEvent`) over the `frigate_client`
and `archive_store` repo adapters; both external systems are wrapped in repo/.
"""

import logging
from datetime import UTC, datetime

from app.config import settings
from app.repo import archive_store as store
from app.repo import frigate_client as frigate
from app.types import ArchiveEvent

logger = logging.getLogger(__name__)


def _to_dt(epoch: float | None) -> datetime | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC)


def _build_event(raw: dict) -> ArchiveEvent | None:
    """Map a raw Frigate event dict into our ArchiveEvent model."""
    event_id = raw.get("id")
    camera = raw.get("camera")
    label = raw.get("label")
    start = _to_dt(raw.get("start_time"))
    if not event_id or not camera or not label or start is None:
        logger.warning("Skipping malformed Frigate event: %s", event_id)
        return None
    return ArchiveEvent(
        id=str(event_id),
        camera=str(camera),
        label=str(label),
        score=float(raw.get("top_score") or raw.get("data", {}).get("top_score") or 0.0),
        zones=list(raw.get("zones") or []),
        start_time=start,
        end_time=_to_dt(raw.get("end_time")),
        archived_at=store.now_utc(),
    )


def archive_event(raw: dict) -> ArchiveEvent | None:
    """Archive a single Frigate event: media -> B2, record -> JSONL index.

    Returns the persisted ArchiveEvent, or None if the raw event was malformed.
    Raises RuntimeError if Frigate or B2 IO fails (the caller decides whether to
    keep polling).
    """
    event = _build_event(raw)
    if event is None:
        return None

    clip = frigate.download_clip(event.id)
    if clip is not None:
        key = store.event_clip_key(event.camera, event.id)
        event.clip_bytes = store.put_bytes(key, clip, "video/mp4")
        event.clip_key = key
        event.has_clip = True

    snapshot = frigate.download_snapshot(event.id)
    if snapshot is not None:
        key = store.event_snapshot_key(event.camera, event.id)
        event.snapshot_bytes = store.put_bytes(key, snapshot, "image/jpeg")
        event.snapshot_key = key
        event.has_snapshot = True

    store.append_event(event)
    _touch_camera_registry(event)
    logger.info(
        "Archived event %s (camera=%s label=%s clip=%s snapshot=%s bytes=%d)",
        event.id,
        event.camera,
        event.label,
        event.has_clip,
        event.has_snapshot,
        event.clip_bytes + event.snapshot_bytes,
    )
    return event


def _touch_camera_registry(event: ArchiveEvent) -> None:
    """Keep `index/cameras.json` current with last-seen per camera."""
    registry = store.read_cameras()
    cam = registry.get(event.camera, {})
    cam["last_event_at"] = event.start_time.isoformat()
    cam["last_label"] = event.label
    registry[event.camera] = cam
    store.write_cameras(registry)


def archive_recent(limit: int | None = None, after: float | None = None) -> dict:
    """Pull recent Frigate events and archive any not already in the index.

    Returns a small summary dict ({scanned, archived, bytes}). Designed to be
    called once per poll by the CLI worker (scripts/archive_worker.py) or on
    demand from the API.
    """
    cap = limit or settings.archive_event_limit
    raw_events = frigate.list_events(limit=cap, after=after)
    archived = 0
    total_bytes = 0
    seen = _existing_ids_for(raw_events)
    for raw in raw_events:
        if str(raw.get("id")) in seen:
            continue
        event = archive_event(raw)
        if event is not None:
            archived += 1
            total_bytes += event.clip_bytes + event.snapshot_bytes
    return {"scanned": len(raw_events), "archived": archived, "bytes": total_bytes}


def _existing_ids_for(raw_events: list[dict]) -> set[str]:
    """Collect already-archived event ids for the days the raw events touch,
    so a re-poll never double-writes the same event."""
    days: set[str] = set()
    for raw in raw_events:
        dt = _to_dt(raw.get("start_time"))
        if dt is not None:
            days.add(dt.date().isoformat())
    existing: set[str] = set()
    for day in days:
        existing.update(e.id for e in store.read_index_day(day))
    return existing
