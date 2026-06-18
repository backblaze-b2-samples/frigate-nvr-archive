"""HTTP surface for the event timeline, search, dashboard stats, and the
archive trigger. No business logic here — handlers validate input, delegate to
the service layer, and map domain errors to HTTP."""

import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.service import stats as stats_service
from app.service.archive import archive_recent
from app.service.events import EventError, clip_download_url, get_event, search_events
from app.types import DailyWriteVolume, EventFilters, EventView, NvrStats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/events/stats", response_model=NvrStats)
async def nvr_stats_endpoint():
    return stats_service.get_nvr_stats()


@router.get("/events/stats/write-volume", response_model=list[DailyWriteVolume])
async def write_volume_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return stats_service.get_write_volume(days=days)


@router.get("/events", response_model=list[EventView])
async def search_events_endpoint(
    camera: str | None = None,
    label: str | None = None,
    zone: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
):
    filters = EventFilters(
        camera=camera,
        label=label,
        zone=zone,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    try:
        return search_events(filters)
    except EventError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/events/{event_id}", response_model=EventView)
async def get_event_endpoint(event_id: str):
    try:
        return get_event(event_id)
    except EventError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/events/{event_id}/clip")
async def event_clip_endpoint(event_id: str):
    try:
        return {"url": clip_download_url(event_id)}
    except EventError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/events/archive")
async def archive_now_endpoint():
    """On-demand pull of recent Frigate events into the B2 archive. The standing
    worker (scripts/archive_worker.py) does this on a loop; this endpoint lets
    the UI trigger a one-shot sync.

    Bounded to `archive_sync_limit` newly-archived events so the request returns
    in seconds and the button gets a prompt confirmation; repeated clicks drain
    any remaining backlog. A transient clip error for one event is already
    swallowed in the repo/service layer, so a pass completes instead of aborting.
    """
    try:
        return archive_recent(max_new=settings.archive_sync_limit)
    except RuntimeError as e:
        # Frigate or B2 unreachable — surface as 502 so the UI can explain.
        raise HTTPException(status_code=502, detail=str(e)) from None
