"""Event timeline & search over the JSONL index stored in B2.

Search loads the index partitions for the queried date range from B2 and filters
by camera / object class (label) / zone / time, then returns events enriched with
short-lived presigned snapshot + clip URLs so the browser streams media straight
from B2. No database — the JSONL index in B2 is the search backend.
"""

import logging
from datetime import UTC, date, datetime, timedelta

from app.repo import archive_store as store
from app.types import ArchiveEvent, EventFilters, EventView

logger = logging.getLogger(__name__)

# Default lookback when no date range is supplied.
DEFAULT_RANGE_DAYS = 7
MAX_RANGE_DAYS = 90


class EventError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _parse_day(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as e:
        raise EventError(f"Invalid date '{value}', expected YYYY-MM-DD") from e


def _resolve_range(filters: EventFilters) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    end = _parse_day(filters.end_date, today)
    start = _parse_day(
        filters.start_date, end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    )
    if start > end:
        raise EventError("start_date must not be after end_date")
    if (end - start).days > MAX_RANGE_DAYS:
        raise EventError(f"Date range too wide (max {MAX_RANGE_DAYS} days)")
    return start, end


def _matches(event: ArchiveEvent, filters: EventFilters) -> bool:
    if filters.camera and event.camera != filters.camera:
        return False
    if filters.label and event.label != filters.label:
        return False
    return not (filters.zone and filters.zone not in event.zones)


def _to_view(event: ArchiveEvent) -> EventView:
    clip_url = store.presign_get(event.clip_key) if event.clip_key else None
    snapshot_url = (
        store.presign_get(event.snapshot_key) if event.snapshot_key else None
    )
    return EventView(
        **event.model_dump(),
        clip_url=clip_url,
        snapshot_url=snapshot_url,
    )


def search_events(filters: EventFilters) -> list[EventView]:
    """Return matching events (newest first) with presigned playback URLs."""
    start, end = _resolve_range(filters)
    events = store.read_index_range(start, end)
    matched = [e for e in events if _matches(e, filters)]
    matched.sort(key=lambda e: e.start_time, reverse=True)
    limit = max(1, min(filters.limit or 100, 500))
    return [_to_view(e) for e in matched[:limit]]


def get_event(event_id: str) -> EventView:
    """Look up a single event across the index (newest days first)."""
    for day in store.list_index_days():
        for event in store.read_index_day(day):
            if event.id == event_id:
                return _to_view(event)
    raise EventError("Event not found", status_code=404)


def clip_download_url(event_id: str) -> str:
    """Presigned attachment URL to download an event's clip from B2."""
    event = get_event(event_id)
    if not event.clip_key:
        raise EventError("Event has no archived clip", status_code=404)
    return store.presign_download(event.clip_key, f"{event.camera}-{event.id}.mp4")
