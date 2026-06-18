"""HTTP surface for the Archive Library (scoped explorer over the app's own B2
prefix). No business logic here — delegate to service/archive_browse."""

import logging

from fastapi import APIRouter, HTTPException

from app.service.archive_browse import (
    ArchiveBrowseError,
    get_overview,
    list_camera_dates,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/archive")
async def archive_overview_endpoint():
    """Per-camera roll-up of this app's archive prefix on B2."""
    return get_overview()


@router.get("/archive/cameras/{camera}/dates")
async def archive_camera_dates_endpoint(camera: str):
    try:
        return list_camera_dates(camera)
    except ArchiveBrowseError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
